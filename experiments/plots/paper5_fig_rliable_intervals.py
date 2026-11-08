"""Online Resource 1, figure audit: interval plot of the rliable results (Online Resource 2 gives the numbers).

a, interquartile mean (IQM) of priority-slice compliance and b, of reward per gNB per step, each with its stratified
bootstrap 95% CI; c and d, the probability that a run of AXIOM beats a run of each other policy on the same two
measures, ties counted as one half, with its CI, and a dashed line at one half. One row per setting. Every value is
read from experiments/results/m93/m93_summary.json (rliable 1.2.0), which m66_verify recomputes from the logs.
Tokens of figures/axiom_style.py. Every plotted number is written to <out>_summary.json.
"""
import json
import sys

import numpy as np

sys.path.insert(0, "/home/kmanojp/oranslice_rig/Papers_4-5/Paper_5/WPC/figures")
import axiom_style as S  # noqa: E402

S.setup()
SUMMARY = "/home/kmanojp/oranslice_rig/experiments/results/m93/m93_summary.json"
OUT = "/home/kmanojp/oranslice_rig/Papers_4-5/Paper_5/WPC/figures/fig_rliable_intervals"
ORDER = ("Env A, 3 gNBs", "Env A, 7 gNBs", "Env A, 19 gNBs", "Env A, 37 gNBs", "Env B, 3 gNBs", "Env B, 7 gNBs", "Env B, 19 gNBs")
KEY = {"AXIOM": "axiom2", "MAPPO": "mappo_tuned", "DQN-SA": "single_agent_dqn", "DQN-I": "independent_dqn",
       "Static rule": "rule_static", "Tuned rule": "rule_local"}
POL = ["AXIOM", "MAPPO", "DQN-SA", "DQN-I", "Static rule", "Tuned rule"]


def main():
    d = json.load(open(SUMMARY))
    fig = S.figure("full", 150)
    fw, fh = (lambda mm: mm / 119.0), (lambda mm: mm / 150.0)
    axes = {"iqm_prio": fig.add_axes([fw(26), fh(80), fw(40), fh(62)]), "iqm_reward": fig.add_axes([fw(76), fh(80), fw(40), fh(62)]),
            "poi_prio": fig.add_axes([fw(26), fh(15), fw(40), fh(50)]), "poi_reward": fig.add_axes([fw(76), fh(15), fw(40), fh(50)])}
    off = {p: (i - 2.5) * 0.12 for i, p in enumerate(POL)}
    out = {}
    for r, name in enumerate(ORDER):
        pols = d["settings"][name]["policies"]
        out[name] = {}
        for p in POL:
            if p not in pols:
                continue
            v = pols[p]; out[name][p] = {}
            for m in ("iqm_prio", "iqm_reward", "poi_prio", "poi_reward"):
                if m.startswith("poi") and p == "AXIOM":
                    continue
                y = r + off[p]
                lo, hi = v[f"{m}_ci"]
                ax = axes[m]
                ax.plot([lo, hi], [y, y], color=S.POLICY[KEY[p]]["color"], lw=0.9, zorder=2)
                ax.plot([v[m]], [y], zorder=3, **S.marker_kw(KEY[p], 3.0))
                out[name][p][m] = [v[m], lo, hi]
    for m, ax in axes.items():
        ax.set_ylim(len(ORDER) - 0.5, -0.5)
        ax.set_yticks(range(len(ORDER)))
        ax.set_yticklabels(ORDER if m in ("iqm_prio", "poi_prio") else [])
        ax.tick_params(axis="y", length=0)
        for k in range(len(ORDER) - 1):
            ax.axhline(k + 0.5, color="#E3E3E3", lw=0.4, zorder=0)
        ax.axhline(3.5, color="#BBBBBB", lw=0.6, zorder=0)
        if m.startswith("poi"):
            ax.axvline(0.5, color=S.INK, lw=0.6, ls=(0, (3, 2)), zorder=1); ax.set_xlim(-0.03, 1.03); ax.set_xticks([0, 0.5, 1])
    axes["iqm_prio"].set_xlabel("IQM priority-slice\ncompliance (%)")
    axes["iqm_reward"].set_xlabel("IQM reward per gNB\nper step")
    axes["poi_prio"].set_xlabel("P(AXIOM better),\ncompliance")
    axes["poi_reward"].set_xlabel("P(AXIOM better),\nreward")
    for t, ax in zip("abcd", (axes["iqm_prio"], axes["iqm_reward"], axes["poi_prio"], axes["poi_reward"])):
        ax.text(-0.05 if t in "bd" else -0.55, 1.02, t, transform=ax.transAxes, fontweight="bold", va="bottom")
    from matplotlib.lines import Line2D
    hs = [Line2D([], [], color=S.POLICY[KEY[p]]["color"], lw=0.9, label=p, **{k: v for k, v in S.marker_kw(KEY[p], 3.0).items() if k != "ls"})
          for p in POL]
    fig.legend(handles=hs, loc="upper center", ncol=6, bbox_to_anchor=(0.5, 1.0), handletextpad=0.2, columnspacing=0.8, handlelength=1.4)
    json.dump(out, open(OUT + "_summary.json", "w"), indent=1)
    print(S.save(fig, OUT))


if __name__ == "__main__":
    main()
