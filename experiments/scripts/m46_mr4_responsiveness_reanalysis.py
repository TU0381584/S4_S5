#!/usr/bin/env python3
"""M46-MR4 -- NO RIG. Re-analyzes MR3's and MR3c's already-collected
gNB logs under a direction-correct, per-slice expected-sign definition
of state-responsiveness (see docs/PAPER5_M46_MR4_responsiveness_spec_and_reanalysis.md
for the derivation from reward.py's actual accounting -- this script
only recomputes the numbers that doc reports, it does not re-derive
the expected signs itself).

Two cutoffs, matched to what each run's logs actually contain:
- MR3 (pre-fix, predates the M46DBG e2_apply instrumentation):
  t>=30s proxy, reusing the exact method MR3b's own correction used.
- MR3c (post-fix, has M46DBG e2_apply): precise
  t>=first_e2_apply_write per slice, as validated in
  docs/PAPER5_M46_MR3c_clean_revalidation.md.

Writes results/m46_mr4/manifest.csv. No live rig access; reads
existing gnb_m41_*.log files under experiments/logs/ only.
"""
import json
import re
import statistics as stats
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m44e2b_ceiling_bind_check as m44e2b  # noqa: E402

RIG = Path(__file__).resolve().parent.parent.parent
E2_RE = re.compile(r"M46DBG e2_apply t=([\d.]+) sst=(\d+) sd=([0-9a-f]+)")
SID_KEY = {3: (1, "000001"), 1: (1, "ffffff")}  # urllc, embb
EXPECTED_SIGN = {"urllc": "+", "embb": "-"}


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


def classify(r, expected):
    if r is None:
        return "no_signal"
    if expected == "+":
        return "match" if r > 0.1 else ("negligible" if r > -0.1 else "contradict")
    return "match" if r < -0.1 else ("negligible" if r < 0.1 else "contradict")


def clean_mr3_original(gnb_log: Path, sid: int) -> tuple:
    full = m44e2b.parse_m41dbg(gnb_log, 0)
    ceil = sorted([row for row in full["ceiling_rows"] if row["sid"] == sid], key=lambda x: x["t"])
    post = sorted([row for row in full["postpf_rows"] if row["sid"] == sid], key=lambda x: x["t"])
    if not ceil:
        return None, 0
    t0 = ceil[0]["t"]
    ceil_c = [row for row in ceil if row["t"] - t0 >= 30.0]
    post_c = [row for row in post if row["t"] - t0 >= 30.0]
    n = min(len(ceil_c), len(post_c))
    maxp = [row["max_prbs"] for row in ceil_c[:n]]
    remain = [row["remainUEs"] for row in post_c[:n]]
    return pearson(remain, maxp)


def clean_mr3c(gnb_log: Path, sid: int) -> tuple:
    full = m44e2b.parse_m41dbg(gnb_log, 0)
    e2_first = {}
    for line in gnb_log.read_text(errors="ignore").splitlines():
        m = E2_RE.search(line)
        if m:
            key = (int(m.group(2)), m.group(3))
            e2_first.setdefault(key, float(m.group(1)))
    key = SID_KEY[sid]
    fw = e2_first.get(key)
    ceil = sorted([row for row in full["ceiling_rows"] if row["sid"] == sid], key=lambda x: x["t"])
    post = sorted([row for row in full["postpf_rows"] if row["sid"] == sid], key=lambda x: x["t"])
    if fw is None or not ceil:
        return None, 0
    ceil_c = [row for row in ceil if row["t"] >= fw]
    post_c = [row for row in post if row["t"] >= fw]
    n = min(len(ceil_c), len(post_c))
    maxp = [row["max_prbs"] for row in ceil_c[:n]]
    remain = [row["remainUEs"] for row in post_c[:n]]
    return pearson(remain, maxp)


def main() -> int:
    out_dir = RIG / "experiments/results/m46_mr4"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []

    mr3 = json.loads((RIG / "experiments/results/m46_mr3/all_runs.json").read_text())
    for r in mr3:
        for sid, slice_name in [(3, "urllc"), (1, "embb")]:
            gnb_log = RIG / f"experiments/logs/gnb_m41_{r['ts2']}.log"
            corr, n = clean_mr3_original(gnb_log, sid)
            rows.append({
                "era": "MR3_orig_t30s_proxy", "mode": r["mode"], "train_seed": r["train_seed"],
                "slice": slice_name, "expected_sign": EXPECTED_SIGN[slice_name],
                "pearson_r": corr, "n": n, "classification": classify(corr, EXPECTED_SIGN[slice_name]),
            })

    mr3c = json.loads((RIG / "experiments/results/m46_mr3c/all_runs.json").read_text())
    for r in mr3c:
        for sid, slice_name in [(3, "urllc"), (1, "embb")]:
            gnb_log = RIG / f"experiments/logs/gnb_m41_{r['ts2']}.log"
            corr, n = clean_mr3c(gnb_log, sid)
            rows.append({
                "era": "MR3c_clean_firstwrite", "mode": r["mode"], "train_seed": r["train_seed"],
                "slice": slice_name, "expected_sign": EXPECTED_SIGN[slice_name],
                "pearson_r": corr, "n": n, "classification": classify(corr, EXPECTED_SIGN[slice_name]),
            })

    import csv
    with open(out_dir / "manifest.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["era", "mode", "train_seed", "slice", "expected_sign", "pearson_r", "n", "classification"])
        w.writeheader()
        w.writerows(rows)
    for row in rows:
        print(row, file=sys.stderr)
    print(f"[m46-mr4] wrote {out_dir / 'manifest.csv'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
