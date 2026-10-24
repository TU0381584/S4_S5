#!/usr/bin/env python3
"""Per-layout priority-slice compliance in Env A at 19 and 37 gNBs (Online Resource 1).

(a) 19 gNBs, every learned arm under each layout, seeds 900-926 and 1000-1002
    (m65_scaling/n19_{layout}).
(b) 37 gNBs (M73): AXIOM under each layout (30 hex seeds, 15 ring, 15
    fully-connected). The baselines never read the layout in Env A and ran once,
    on the hex seeds, so they are drawn at the hex position only.
Per-seed points behind the mean and 95% bootstrap CI. Every plotted number is
written to <out>_summary.json.

Usage: paper5_fig_layouts.py --out Papers_4-5/Paper_5/WPC/figures/fig14_layouts
"""
import argparse
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/scripts")
sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/plots")
from m62_analysis import boot_ci  # noqa: E402
from m66_verify import S15, S30_19, prio, seeds_of  # noqa: E402
from paper5_common import M2_ARM_STYLE, SUPP_WIDTH_IN, panel  # noqa: E402

ARMS = ["axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned"]
LAYOUTS = ["fully_connected", "ring", "hex"]
LAB = {"fully_connected": "Fully-\nconnected", "ring": "Ring", "hex": "Hex"}


def rows(n, arm, t):
    if n == 19:
        return seeds_of(f"m65_scaling/n19_{t}", arm, S30_19)
    if arm == "axiom2":
        return seeds_of(f"m73/A_n37_{t}", arm, S30_19 if t == "hex" else S15)
    return seeds_of("m73/A_n37_hex", arm, S30_19) if t == "hex" else {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    fig, axs = plt.subplots(1, 2, figsize=(SUPP_WIDTH_IN, 2.5), sharey=True)
    rng = np.random.RandomState(0)
    summ = {}
    w = 0.18
    for ax, n in zip(axs, (19, 37)):
        for i, arm in enumerate(ARMS):
            st = M2_ARM_STYLE[arm]
            for xi, t in enumerate(LAYOUTS):
                v = [100 * prio(r) for r in rows(n, arm, t).values()]
                if not v:
                    continue
                x0 = xi + (i - 1.5) * w
                lo, hi = boot_ci(v)
                m = float(np.mean(v))
                ax.scatter(x0 + rng.uniform(-0.04, 0.04, len(v)), v, s=4, color=st["color"], alpha=0.3, lw=0)
                ax.errorbar(x0, m, yerr=[[m - lo], [hi - m]], fmt=st["marker"], color=st["color"], ms=4.5 if arm == "axiom2" else 3.5,
                            capsize=2, lw=1.0, label=st["label"].replace(" (proposed)", "") if (xi == 2 and n == 19) else None)
                summ.setdefault(str(n), {}).setdefault(arm, {})[t] = {"n": len(v), "mean": m, "ci": [lo, hi]}
        ax.set_xticks(range(3))
        ax.set_xticklabels([LAB[t] for t in LAYOUTS], fontsize=8)
        panel(ax, "a" if n == 19 else "b")
        ax.grid(True, axis="y", lw=0.4, alpha=0.4)
        ax.spines[["top", "right"]].set_visible(False)
    axs[0].set_ylabel("Priority-slice SLA, %", fontsize=8)
    axs[0].set_ylim(-3, 103)
    fig.legend(loc="lower center", ncol=4, frameon=False, fontsize=8, bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(rect=(0, 0.09, 1, 1))
    fig.savefig(a.out + ".pdf", bbox_inches="tight")
    fig.savefig(a.out + ".png", dpi=200, bbox_inches="tight")
    json.dump(summ, open(a.out + "_summary.json", "w"), indent=1)
    for n, d in summ.items():
        print(n, {arm: {t: (x["n"], round(x["mean"], 1)) for t, x in v.items()} for arm, v in d.items()})


if __name__ == "__main__":
    main()
