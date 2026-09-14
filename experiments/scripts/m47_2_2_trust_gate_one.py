#!/usr/bin/env python3
"""M47-2-2 -- runs ONE checkpoint's live trust-gate (cold-start, E4
co-located regime, contention gate, MR3c protocol) and appends its
PASS/FAIL result to experiments/results/m47_2_2/manifest.csv.
Deliberately one-checkpoint-per-process-invocation (not a loop over
many) so the orchestrating session can git-commit after every single
checkpoint clears, per this milestone's own standing constraint that a
mid-block rig hang must lose at most one in-flight run.

Reuses m46_mr3_live_revalidate.run_one() UNCHANGED (same cold-start,
contention gate, E4 regime, MR1 config) and the exact same clean-
window method MR3c/PF2-1a/PF2-1b established (t>=first M46DBG
e2_apply write per slice) -- no new methodology invented for this
gate, just applied to 12 more checkpoints.

Usage: m47_2_2_trust_gate_one.py <mode> <seed>
"""
import csv
import json
import re
import statistics as stats
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m46_mr3_live_revalidate as mr3  # noqa: E402
import m44e2b_ceiling_bind_check as m44e2b  # noqa: E402

RIG = mr3.RIG
mr3.OUT_DIR = RIG / "experiments/results/m47_2_2"
mr3.OUT_DIR.mkdir(parents=True, exist_ok=True)

E2_RE = re.compile(r"M46DBG e2_apply t=([\d.]+) sst=(\d+) sd=([0-9a-f]+)")
SID_KEY = {3: (1, "000001"), 1: (1, "ffffff")}
SID_NAME = {3: "urllc", 1: "embb"}
UNCAPPED_THRESHOLD = 90


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
    mode, seed = sys.argv[1], int(sys.argv[2])
    eval_seed_map = {261: 969, 262: 970, 263: 971, 264: 972, 265: 973, 266: 974, 267: 975}
    eval_seed = eval_seed_map[seed] + (0 if mode == "qoe" else 100)

    print(f"[m47-2-2] === trust-gating {mode}/seed{seed} (eval_seed={eval_seed}) ===", file=sys.stderr)
    result = mr3.run_one(mode, seed, eval_seed, 1, 1)

    row = {
        "mode": mode, "train_seed": seed, "eval_seed": eval_seed,
        "error": result.get("error"), "coupling_pass": result.get("error") is None,
    }

    if result.get("error") is not None:
        row.update({
            "urllc_uncapped_n": None, "embb_uncapped_n": None,
            "in_band_pass": False, "urllc_r": None, "embb_r": None,
            "responsiveness_pass": False, "pwc": None, "pwc_eq": None,
            "shed_classification": None, "overall_pass": False,
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

        in_band_ok = True
        resp_ok = True
        per_slice = {}
        for sid, name in SID_NAME.items():
            key = SID_KEY[sid]
            fw = e2_first.get(key)
            ceil = sorted([r for r in full["ceiling_rows"] if r["sid"] == sid], key=lambda x: x["t"])
            post = sorted([r for r in full["postpf_rows"] if r["sid"] == sid], key=lambda x: x["t"])
            if fw is None or not ceil:
                in_band_ok = False
                resp_ok = False
                per_slice[name] = {"uncapped_n": None, "r": None}
                continue
            ceil_c = [r for r in ceil if r["t"] >= fw]
            post_c = [r for r in post if r["t"] >= fw]
            n = min(len(ceil_c), len(post_c))
            uncapped_n = sum(1 for r in ceil_c if r["max_prbs"] >= UNCAPPED_THRESHOLD)
            if uncapped_n > 0:
                in_band_ok = False
            maxp = [r["max_prbs"] for r in ceil_c[:n]]
            remain = [r["remainUEs"] for r in post_c[:n]]
            r0, n0 = pearson(remain, maxp)
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
            "overall_pass": in_band_ok and resp_ok and row["coupling_pass"],
        })

    manifest = RIG / "experiments/results/m47_2_2/manifest.csv"
    fieldnames = ["mode", "train_seed", "eval_seed", "error", "coupling_pass",
                  "urllc_uncapped_n", "embb_uncapped_n", "in_band_pass",
                  "urllc_r", "embb_r", "responsiveness_pass",
                  "pwc", "pwc_eq", "shed_classification", "overall_pass"]
    write_header = not manifest.exists()
    with open(manifest, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        if write_header:
            w.writeheader()
        w.writerow(row)

    print(f"[m47-2-2] {mode}/seed{seed}: overall_pass={row['overall_pass']} "
          f"in_band={row.get('in_band_pass')} responsiveness={row.get('responsiveness_pass')} "
          f"coupling={row['coupling_pass']} error={row['error']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
