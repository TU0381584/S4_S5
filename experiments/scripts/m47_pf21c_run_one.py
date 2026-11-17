#!/usr/bin/env python3
"""M47-PF2-1c -- runs ONE (slot, arm) live cell (cold-start, E4
co-located regime, contention gate, MR3c protocol) and appends its
PWC/PWC_eq/shed-classification (characterization, not a pass/fail
gate -- see docs/PAPER5_M47_PF21c_plan_and_deviation.md) plus in-band/
responsiveness/coupling diagnostics to
experiments/results/m47_pf21c/manifest.csv. One cell per process
invocation, matching M47-2-2's own resumability discipline (git
commit after every single run).

Usage: m47_pf21c_run_one.py <draw> <slot_seed> <arm> <eval_seed>
  draw: "primary" or "replication"
  slot_seed: the DQN checkpoint seed for this slot (258/260/261/263/264/267)
  arm: dqn_qoe | dqn_sla | static_cap | static_floor | lb_only
  eval_seed: the environmental arrival-process seed for this run
"""
import csv
import re
import statistics as stats
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m46_mr3_live_revalidate as mr3  # noqa: E402
import m44e2b_ceiling_bind_check as m44e2b  # noqa: E402

RIG = mr3.RIG
mr3.OUT_DIR = RIG / "experiments/results/m47_pf21c"
mr3.OUT_DIR.mkdir(parents=True, exist_ok=True)

E2_RE = re.compile(r"M46DBG e2_apply t=([\d.]+) sst=(\d+) sd=([0-9a-f]+)")
SID_KEY = {3: (1, "000001"), 1: (1, "ffffff")}
SID_NAME = {3: "urllc", 1: "embb"}
UNCAPPED_THRESHOLD = 90

STATIC_CAP_CFG = RIG / "experiments/configs/m47/saclb_m47_static_at_cap.yaml"
STATIC_FLOOR_CFG = RIG / "experiments/configs/m47/saclb_m47_static_at_floor.yaml"


def pearson(xs, ys):
    pts = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pts) < 3:
        return None, len(pts)
    xv = [p[0] for p in pts]
    yv = [p[1] for p in pts]
    if stats.pstdev(xv) == 0 or stats.pstdev(yv) == 0:
        return None, len(pts)
    mx, my = stats.mean(xv), stats.mean(yv)
    cov = sum((x - mx) * (y - my) for x, y in pts) / len(pts)
    return cov / (stats.pstdev(xv) * stats.pstdev(yv)), len(pts)


def main() -> int:
    draw, slot_seed, arm, eval_seed = sys.argv[1], int(sys.argv[2]), sys.argv[3], int(sys.argv[4])

    if arm == "dqn_qoe":
        kwargs = dict(mode="qoe", train_seed=slot_seed)
    elif arm == "dqn_sla":
        kwargs = dict(mode="sla", train_seed=slot_seed)
    elif arm == "static_cap":
        kwargs = dict(mode="static_cap", train_seed=slot_seed, algorithm="lb_only",
                       config_override=STATIC_CAP_CFG, reward_mode_override="sla")
    elif arm == "static_floor":
        kwargs = dict(mode="static_floor", train_seed=slot_seed, algorithm="lb_only",
                       config_override=STATIC_FLOOR_CFG, reward_mode_override="sla")
    elif arm == "lb_only":
        kwargs = dict(mode="lb_only", train_seed=slot_seed, algorithm="lb_only",
                       reward_mode_override="sla")
    else:
        raise ValueError(f"unknown arm {arm!r}")

    print(f"[pf21c] === {draw} slot={slot_seed} arm={arm} eval_seed={eval_seed} ===", file=sys.stderr)
    result = mr3.run_one(eval_seed=eval_seed, run_idx=1, total=1, **kwargs)

    row = {
        "draw": draw, "slot_seed": slot_seed, "arm": arm, "eval_seed": eval_seed,
        "error": result.get("error"), "coupling_pass": result.get("error") is None,
    }

    if result.get("error") is not None:
        row.update({
            "urllc_uncapped_n": None, "embb_uncapped_n": None, "in_band_pass": False,
            "urllc_r": None, "embb_r": None, "responsiveness_pass": False,
            "pwc": None, "pwc_eq": None, "shed_classification": None,
        })
    else:
        ts2 = result["ts2"]
        gnb_log = RIG / f"experiments/logs/gnb_m41_{ts2}.log"
        full = m44e2b.parse_m41dbg(gnb_log, 0)
        e2_first = {}
        for line in gnb_log.read_text(errors="ignore").splitlines():
            m = E2_RE.search(line)
            if m:
                key = (int(m.group(2)), m.group(3))
                e2_first.setdefault(key, float(m.group(1)))

        in_band_ok, resp_ok = True, True
        per_slice = {}
        for sid, name in SID_NAME.items():
            key = SID_KEY[sid]
            fw = e2_first.get(key)
            ceil = sorted([r for r in full["ceiling_rows"] if r["sid"] == sid], key=lambda x: x["t"])
            post = sorted([r for r in full["postpf_rows"] if r["sid"] == sid], key=lambda x: x["t"])
            if fw is None or not ceil:
                # non-learning arms with no E2 write for a slice that never got a
                # policy-driven update (e.g. lb_only with no accepted requests this
                # episode) -- fall back to the whole run rather than failing closed
                ceil_c, post_c = ceil, post
            else:
                ceil_c = [r for r in ceil if r["t"] >= fw]
                post_c = [r for r in post if r["t"] >= fw]
            n = min(len(ceil_c), len(post_c))
            uncapped_n = sum(1 for r in ceil_c if r["max_prbs"] >= UNCAPPED_THRESHOLD)
            if uncapped_n > 0:
                in_band_ok = False
            r0, n0 = pearson([r["remainUEs"] for r in post_c[:n]], [r["max_prbs"] for r in ceil_c[:n]])
            if r0 is None:
                resp_ok = False
            per_slice[name] = {"uncapped_n": uncapped_n, "r": r0}

        row.update({
            "urllc_uncapped_n": per_slice["urllc"]["uncapped_n"],
            "embb_uncapped_n": per_slice["embb"]["uncapped_n"],
            "in_band_pass": in_band_ok,
            "urllc_r": per_slice["urllc"]["r"], "embb_r": per_slice["embb"]["r"],
            "responsiveness_pass": resp_ok,
            "pwc": result["pwc"].get("pwc"), "pwc_eq": result["pwc"].get("pwc_equal_weight"),
            "shed_classification": result["pwc"].get("shedding", {}).get("window_classes", [None])[0],
        })

    manifest = RIG / "experiments/results/m47_pf21c/manifest.csv"
    fieldnames = ["draw", "slot_seed", "arm", "eval_seed", "error", "coupling_pass",
                  "urllc_uncapped_n", "embb_uncapped_n", "in_band_pass",
                  "urllc_r", "embb_r", "responsiveness_pass",
                  "pwc", "pwc_eq", "shed_classification"]
    write_header = not manifest.exists()
    with open(manifest, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        if write_header:
            w.writeheader()
        w.writerow(row)

    print(f"[pf21c] {draw}/{slot_seed}/{arm}: pwc={row.get('pwc')} shed={row.get('shed_classification')} "
          f"in_band={row.get('in_band_pass')} coupling={row['coupling_pass']} error={row['error']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
