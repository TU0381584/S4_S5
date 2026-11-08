"""Fig: what AXIOM learned about shedding eMBB in Env B at seven gNBs (ring), 300 against 900 training episodes.

Reads the M81 probe (experiments/scripts/m81_decision_probe.py), which replayed every checkpoint's held-out
evaluation exactly (its rewards match the stored logs) and recorded, for every gNB at every step, the gNB's own
URLLC queue and whether AXIOM's eMBB head would reject. (a) Share of gNB-steps on which AXIOM would shed an eMBB
request, by URLLC queue, pooled over 15 seeds, with 95% bootstrap CIs over seeds, against the tuned rule, which sheds
eMBB once the queue reaches 0.2. Above it, as a marginal, how often each URLLC queue level is visited. Every plotted number is written to
<out>_summary.json, which m66_verify checks.
"""
import glob
import json
import sys

import numpy as np
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/plots")
sys.path.insert(0, "/home/kmanojp/oranslice_rig/Papers_4-5/Paper_5/WPC/figures")
import axiom_style as S  # noqa: E402
S.setup()

PROBE = "/home/kmanojp/oranslice_rig/experiments/results/m81"
BINS = [0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.01]
COL = {"300": "#9cc3ec", "900": "#0072B2"}
STY = {"300": (":", "o"), "900": ("-", "s")}
TAG = dict(fc="#f4ead6", ec="#9c7a45", tc="#4f3a15")


def load(budget):
    seeds = []
    for f in sorted(glob.glob(f"{PROBE}/{budget}_seed*.npz")):
        d = np.load(f)
        seeds.append((d["urllc_queue"], d["shed_embb"]))
    return seeds


def shares(seeds, idx=None):
    seeds = seeds if idx is None else [seeds[i] for i in idx]
    u = np.concatenate([q for q, _ in seeds])
    s = np.concatenate([x for _, x in seeds])
    b = np.digitize(u, BINS) - 1
    out = np.full(len(BINS) - 1, np.nan)
    for k in range(len(BINS) - 1):
        m = b == k
        if m.sum() >= 50:
            out[k] = s[m].mean()
    return out, np.bincount(b, minlength=len(BINS) - 1)[: len(BINS) - 1], float(s.mean())


def main():
    out = "../../Papers_4-5/Paper_5/WPC/figures/fig_decision"
    rng = np.random.default_rng(81)
    summary = {"bins": BINS, "budgets": {}}
    for b in ("300", "900"):
        seeds = load(b)
        sh, cnt, overall = shares(seeds)
        boots = np.array([shares(seeds, rng.integers(0, len(seeds), len(seeds)))[0] for _ in range(2000)])
        lo, hi = np.nanpercentile(boots, 2.5, axis=0), np.nanpercentile(boots, 97.5, axis=0)
        summary["budgets"][b] = {"n_seeds": len(seeds), "states": int(cnt.sum()), "overall_shed": overall,
                                 "shed": sh.tolist(), "shed_ci": [lo.tolist(), hi.tolist()], "visits": (cnt / cnt.sum()).tolist()}
    centres = [0.5 * (BINS[k] + min(BINS[k + 1], 2.0)) for k in range(len(BINS) - 1)]
    # figure audit: one panel, with how often each queue level occurs as a marginal on the same queue axis
    fig = S.figure("full", 74)
    fw, fh = (lambda mm: mm / 119.0), (lambda mm: mm / 74.0)
    axA = fig.add_axes([fw(16), fh(17), fw(98), fh(36)])
    axM = fig.add_axes([fw(16), fh(56), fw(98), fh(14)], sharex=axA)
    edges = [min(e, 2.0) for e in BINS]
    for b, lab in (("300", "300 episodes"), ("900", "900 episodes")):
        s_ = summary["budgets"][b]
        y = 100 * np.array(s_["shed"])
        lo, hi = 100 * np.array(s_["shed_ci"][0]), 100 * np.array(s_["shed_ci"][1])
        axA.fill_between(centres, lo, hi, color=S.lighten(COL[b], 0.75), lw=0, zorder=0)   # opaque tint, EPS-safe
        for e_ in (lo, hi):
            axA.plot(centres, e_, color=COL[b], lw=0.4, ls=STY[b][0], zorder=1)
        axA.plot(centres, y, ls=STY[b][0], marker=STY[b][1], color=COL[b], mec="#0072B2", ms=3.6, lw=1.3, label=f"AXIOM, {lab}", zorder=3)
        axM.stairs(100 * np.array(s_["visits"]), edges, color="#0072B2" if b == "900" else COL[b], ls=STY[b][0], lw=1.1)
    axA.step([0, 0.2, 0.2, 2.0], [0, 0, 100, 100], where="post", color="#555555", ls="--", lw=1.0, label="Tuned rule")   # pre-audit colour
    axA.set_xlim(0, 2.0); axA.set_ylim(-3, 103)
    axA.set_xlabel("gNB\u2019s own URLLC queue (share of budget)")
    axA.set_ylabel("eMBB requests\nshed (%)")
    axM.set_ylabel("gNB-steps\n(%)")
    axM.tick_params(axis="x", labelbottom=False)
    fig.legend(*axA.get_legend_handles_labels(), loc="lower center", bbox_to_anchor=(0.55, 0.0), ncol=3, frameon=False, handlelength=2.2)
    S.env_badge(fig, fw(1), fh(73.5), "B", va="top")   # pre-audit badge restored (2026-11-09)
    print(S.save(fig, out))
    json.dump(summary, open(out + "_summary.json", "w"), indent=1)
    for b in ("300", "900"):
        s = summary["budgets"][b]
        print(b, "overall", round(100 * s["overall_shed"], 1), "by bin", [None if np.isnan(x) else round(100 * x, 1) for x in s["shed"]],
              "visits", [round(100 * v, 1) for v in s["visits"]])


if __name__ == "__main__":
    main()
