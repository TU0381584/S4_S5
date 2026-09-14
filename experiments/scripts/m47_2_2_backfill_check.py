#!/usr/bin/env python3
"""M47-2-2 -- applies THIS gate's own pre-committed pass criteria
(in_band: 0 samples max_prbs>=90 in the t>=first_e2_apply_write clean
window, both slices; responsiveness: Pearson r computable, both
slices; coupling: xapp ok=True) retroactively to MR3c's 4 runs
(seeds 256/257) and PF2-1a's 6 runs (seeds 258/259/260), to determine
precisely how many of the ALREADY-COLLECTED prior live runs also
satisfy this gate's exact bar -- not re-run, not re-derived
differently, the identical check m47_2_2_trust_gate_one.py applies to
the 12 new checkpoints, applied to data already on disk. No new live
time. Needed because the >=11/arm decision threshold depends on the
FULL live-validated pool, not just the 6 new seeds in isolation, and
seed 261 was never live-tested at all in any prior milestone.
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
SID_KEY = {3: (1, "000001"), 1: (1, "ffffff")}
SID_NAME = {3: "urllc", 1: "embb"}
UNCAPPED_THRESHOLD = 90


def pearson(xs, ys):
    pts = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pts) < 3:
        return None
    xv = [p[0] for p in pts]
    yv = [p[1] for p in pts]
    if stats.pstdev(xv) == 0 or stats.pstdev(yv) == 0:
        return None
    mx, my = stats.mean(xv), stats.mean(yv)
    cov = sum((x - mx) * (y - my) for x, y in pts) / len(pts)
    return cov / (stats.pstdev(xv) * stats.pstdev(yv))


def check(mode, seed, ts2, ok):
    gnb_log = RIG / f"experiments/logs/gnb_m41_{ts2}.log"
    full = m44e2b.parse_m41dbg(gnb_log, 0)
    e2_first = {}
    for line in gnb_log.read_text(errors="ignore").splitlines():
        m = E2_RE.search(line)
        if m:
            key = (int(m.group(2)), m.group(3))
            e2_first.setdefault(key, float(m.group(1)))

    in_band_ok, resp_ok = True, True
    for sid, name in SID_NAME.items():
        key = SID_KEY[sid]
        fw = e2_first.get(key)
        ceil = sorted([r for r in full["ceiling_rows"] if r["sid"] == sid], key=lambda x: x["t"])
        post = sorted([r for r in full["postpf_rows"] if r["sid"] == sid], key=lambda x: x["t"])
        if fw is None or not ceil:
            in_band_ok = resp_ok = False
            continue
        ceil_c = [r for r in ceil if r["t"] >= fw]
        post_c = [r for r in post if r["t"] >= fw]
        n = min(len(ceil_c), len(post_c))
        if sum(1 for r in ceil_c if r["max_prbs"] >= UNCAPPED_THRESHOLD) > 0:
            in_band_ok = False
        r0 = pearson([r["remainUEs"] for r in post_c[:n]], [r["max_prbs"] for r in ceil_c[:n]])
        if r0 is None:
            resp_ok = False
    overall = in_band_ok and resp_ok and ok
    print(f"{mode}/{seed}: in_band={in_band_ok} responsiveness={resp_ok} coupling={ok} -> overall={overall}")
    return overall


def main():
    mr3c = json.loads((RIG / "experiments/results/m46_mr3c/all_runs.json").read_text())
    pf21a = json.loads((RIG / "experiments/results/m45_pf21/pf21a/all_runs.json").read_text())
    results = {}
    for r in mr3c + pf21a:
        ok = check(r["mode"], r["train_seed"], r["ts2"], r.get("error") is None)
        results[(r["mode"], r["train_seed"])] = ok
    n_qoe = sum(1 for (m, s), ok in results.items() if m == "qoe" and ok)
    n_sla = sum(1 for (m, s), ok in results.items() if m == "sla" and ok)
    print(f"\nprior-run pass count: qoe={n_qoe}/6, sla={n_sla}/6")


if __name__ == "__main__":
    main()
