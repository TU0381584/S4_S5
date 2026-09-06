#!/usr/bin/env python3
"""M42-G1-B: config-floor audit. Read-only forensics, no live rig.

For every slicing config confirmed (not assumed from filename) to back a
live number in Paper #4 or Paper #5, compute each slice's floor/nominal/cap
ratio converted to raw DL PRBs using the SAME conversion M41 instrumented
live and cited from source:

    raw_prbs = (n_rb_sched_init * ratio_pct) // 100

  - Integer division, matching C's `/` on ints -- see
    ORANSlice/oai_ran/openair2/LAYER2/NR_MAC_gNB/gNB_scheduler_dlsch.c
    lines 1526-1528 (dedi_prbs/min_prbs/initial max_prbs) and line 1556
    (max_prbs re-clamped to (n_rb_sched_init * max_ratio)/100).
  - n_rb_sched_init=106 is not a config value -- it's this rig's real
    106-PRB/numerology-1 carrier, confirmed empirically via M41's own
    gNB-side instrumentation (M41DBG ceiling log lines recorded
    n_rb_sched_init=106 in every sample across every M41 live capture).
  - The scheduler's hard minimum grant size is min_rbSize=5
    (gNB_scheduler_dlsch.c:1075, inside pf_dl_slice() -- the specific
    occurrence that gates real scheduling; confirmed unrelated occurrences
    at lines 880 and 1333 do not gate this way, see
    docs/PAPER5_M41_envelope_sweep.md's "Scheduler-side workaround" section).

Verdict per slice:
  OK       floor_raw_prbs >= 5           (the whole range is always safe)
  BROKEN   cap_raw_prbs < 5              (the whole range can never clear the floor)
  MARGINAL everything else (floor < 5 <= cap, or floor < 5 and cap < 7) --
           starts below the floor at reset/nominal and needs a specific
           trajectory (repeated accepts) to escape toward the cap; per M41's
           own live finding, ceilings walk back down toward the floor under
           sustained normal-cadence reject pressure, so a MARGINAL slice's
           real safety depends on run-time dynamics, not just its config.
"""
import csv
import re
from pathlib import Path

RIG = Path("/home/kmanojp/oranslice_rig")
OUT_DIR = RIG / "experiments/results/m42_floor_audit"
N_RB_SCHED_INIT = 106  # confirmed empirically, see module docstring
MIN_RBSIZE = 5

# (config_path, paper, campaign_label, backs) -- "backs" is the specific
# published figure/table/number, resolved via script/doc/log ground truth,
# NOT assumed from filename. See M42-G1 report for the evidence trail per
# row (config_floor_audit_G1_report.md).
CONFIGS = [
    # --- Paper #4 (CACS26), Stage 15 N128 campaign, SUBMITTED manuscript ---
    # Ground truth: run_stage15_n128_campaign.sh's CFG_OF mapping (lines
    # 34-46), independently confirmed in docs/REPRODUCIBILITY.md:33-41, and
    # cross-checked against the omega logs' own recorded "ceilings" values
    # (all 4 arms' recorded live ceilings match these files' ratios, not
    # the non-"_v2" siblings' different iqx_coeffs-adjacent numbers).
    ("experiments/configs/saclb_campaign_baseline_v2.yaml", "Paper4-CACS26",
     "N128 baseline (Static) arm", "main.tex Table tab:results, 'Static' row"),
    ("experiments/configs/saclb_campaign_static_at_cap_v2.yaml", "Paper4-CACS26",
     "N128 static_at_cap arm", "main.tex Table tab:results, 'Static-at-cap' row"),
    ("experiments/configs/saclb_campaign_v2.yaml", "Paper4-CACS26",
     "N128 dqn_sla arm", "main.tex Table tab:results, 'DQN-SLA' row"),
    ("experiments/configs/saclb_campaign_v2.yaml", "Paper4-CACS26",
     "N128 dqn_qoe arm (same config file as dqn_sla)", "main.tex Table tab:results, 'DQN-QoE' row"),

    # --- Paper #5 (WPC), Fig. 8 live anchor cells ---
    # Ground truth: Part 3C (docs/PAPER5_FIG8_validity_check.md) -- the
    # historical omega logs' own recorded ceiling values match this file's
    # ratios exactly (e.g. urllc {min_ratio:1,max_ratio:3}).
    ("experiments/configs/saclb_campaign.yaml", "Paper5-WPC",
     "Fig.8 Original checkpoint @ 3UE (m31_highconf/3ue_20ep)", "WPC Fig. 8, 'Original, 3UE'"),
    ("experiments/configs/saclb_campaign.yaml", "Paper5-WPC",
     "Fig.8 Original checkpoint @ 6UE (m31_highconf/6ue_20ep)", "WPC Fig. 8, 'Original, 6UE'"),
    ("experiments/configs/saclb_campaign.yaml", "Paper5-WPC",
     "Fig.8 Recalibrated checkpoint @ 6UE (m34_realistic_retrain_check/6ue_20ep)", "WPC Fig. 8, 'Recalibrated, 6UE'"),

    # --- Paper #5 (WPC), M8 live single-gNB anchor ---
    # M8's actual live runs (both, per docs/PAPER5_M8_live_anchor.md) used
    # saclb_live.yaml BEFORE the M41 fix (git history: these ratios were in
    # place 2026-07-16 through 2026-09-05, spanning M8's entire run window).
    # The CURRENT file has since been fixed (commit cda9d65) -- reading it
    # now would silently misreport M8's actual historical exposure, so the
    # pre-fix ratios are hardcoded here from git history / commit messages,
    # NOT read from the current (already-fixed) file. See HISTORICAL_SLICES
    # below.
    ("__HISTORICAL__:saclb_live.yaml (pre-M41-fix, 2026-07-16 to 2026-09-05)",
     "Paper5-WPC", "M8 live single-gNB anchor (both runs)",
     "WPC section on the Live Single-gNB Anchor"),

    # --- M41's own fixed config, for comparison (not itself a published number) ---
    ("framework/qoe_oran_framework/configs/saclb_live.yaml", "N/A (M41 fix, post-2026-09-05)",
     "current state of saclb_live.yaml after the M41 fix", "not a published number -- included for contrast"),
]

# Hardcoded historical ratios for configs whose live file has since changed
# (see the __HISTORICAL__ marker above). Source: git log on
# framework/qoe_oran_framework/configs/saclb_live.yaml and this session's
# own M41 fix commit message (cda9d65), not re-derived or guessed.
HISTORICAL_SLICES = {
    "__HISTORICAL__:saclb_live.yaml (pre-M41-fix, 2026-07-16 to 2026-09-05)": [
        ("urllc", 3, 1, 3),
        ("embb", 3, 1, 4),
        ("mmtc", 2, 1, 3),
    ],
}

RATIO_RE = re.compile(
    r"slice_id:\s*(\w+).*?nominal_ratio:\s*(\d+).*?min_ratio_floor:\s*(\d+).*?max_ratio_cap:\s*(\d+)",
    re.DOTALL,
)


def parse_slices(yaml_text: str):
    """Minimal, dependency-free extraction: split on 'slice_id:' blocks and
    pull the three ratio fields with a tolerant regex. Good enough for this
    project's consistently-formatted saclb_*.yaml files; does not attempt
    to be a general YAML parser."""
    slices = []
    # Split into per-slice chunks by looking ahead to the next "- slice_id:"
    # or "reward:" section, since these are list items under `slices:`.
    blocks = re.split(r"\n(?=\s*-\s*slice_id:)", yaml_text)
    for block in blocks:
        m = re.search(r"slice_id:\s*(\w+)", block)
        if not m:
            continue
        slice_id = m.group(1)
        nm = re.search(r"nominal_ratio:\s*(\d+)", block)
        fm = re.search(r"min_ratio_floor:\s*(\d+)", block)
        cm = re.search(r"max_ratio_cap:\s*(\d+)", block)
        if nm and fm and cm:
            slices.append((slice_id, int(nm.group(1)), int(fm.group(1)), int(cm.group(1))))
    return slices


def raw_prbs(ratio_pct: int) -> int:
    return (N_RB_SCHED_INIT * ratio_pct) // 100


def verdict(floor_raw: int, cap_raw: int) -> str:
    if floor_raw >= MIN_RBSIZE:
        return "OK"
    if cap_raw < MIN_RBSIZE:
        return "BROKEN"
    return "MARGINAL"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    seen_missing = []
    for cfg_rel, paper, campaign, backs in CONFIGS:
        if cfg_rel in HISTORICAL_SLICES:
            slice_rows = HISTORICAL_SLICES[cfg_rel]
        else:
            cfg_path = RIG / cfg_rel
            if not cfg_path.exists():
                seen_missing.append(cfg_rel)
                continue
            text = cfg_path.read_text()
            slice_rows = parse_slices(text)
        for slice_id, nominal, floor, cap in slice_rows:
            nominal_raw = raw_prbs(nominal)
            floor_raw = raw_prbs(floor)
            cap_raw = raw_prbs(cap)
            rows.append({
                "paper": paper,
                "campaign": campaign,
                "config": cfg_rel,
                "slice": slice_id,
                "nominal_ratio_pct": nominal,
                "floor_ratio_pct": floor,
                "cap_ratio_pct": cap,
                "nominal_raw_prbs": nominal_raw,
                "floor_raw_prbs": floor_raw,
                "cap_raw_prbs": cap_raw,
                "min_rbSize": MIN_RBSIZE,
                "n_rb_sched_init": N_RB_SCHED_INIT,
                "verdict": verdict(floor_raw, cap_raw),
                "backs": backs,
            })

    out_csv = OUT_DIR / "config_floor_matrix.csv"
    fieldnames = ["paper", "campaign", "config", "slice", "nominal_ratio_pct",
                  "floor_ratio_pct", "cap_ratio_pct", "nominal_raw_prbs",
                  "floor_raw_prbs", "cap_raw_prbs", "min_rbSize",
                  "n_rb_sched_init", "verdict", "backs"]
    with open(out_csv, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"[m42] wrote {len(rows)} rows to {out_csv}")
    if seen_missing:
        print(f"[m42] WARNING: {len(seen_missing)} config path(s) not found, skipped: {seen_missing}")
    broken = [r for r in rows if r["verdict"] == "BROKEN"]
    marginal = [r for r in rows if r["verdict"] == "MARGINAL"]
    print(f"[m42] BROKEN: {len(broken)}  MARGINAL: {len(marginal)}  OK: {len(rows) - len(broken) - len(marginal)}")


if __name__ == "__main__":
    main()
