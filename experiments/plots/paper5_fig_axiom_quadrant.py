"""Fig: AXIOM superiority quadrant -- learned reward quality vs scaling
robustness. Single-panel scatter. Every value is a number already reported
in the WPC manuscript; nothing is re-derived from raw logs here.

x  = mean reward per step at N=3 (Table tab:m2-results), 95% bootstrap CI.
y  = collapse resistance at N=7 = 100 - collapse%, two 12-seed samples
     (Section sec:results-m6); point = sample mean, bar = the two-sample span.

Colours/markers match paper5_common.M2_ARM_STYLE so arm identity stays
consistent with the other result figures. The proposed arm is labelled
AXIOM to match the manuscript text and Table tab:compare.
"""
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

mpl.rcParams.update({
    "font.size": 10, "axes.titlesize": 11, "axes.labelsize": 10,
    "xtick.labelsize": 9, "ytick.labelsize": 9,
    "axes.linewidth": 0.7, "axes.grid": True,
    "grid.linewidth": 0.4, "grid.alpha": 0.4,
    "axes.spines.top": False, "axes.spines.right": False,
    "pdf.fonttype": 42, "ps.fonttype": 42, "savefig.bbox": "tight",
})

# ---- sourced data ----------------------------------------------------------
# name: (reward_mean, [rew_lo, rew_hi]), (resist_mean, [res_lo, res_hi]), style
ARMS = {
    "AXIOM": {
        "x": 14.062, "xci": (13.91, 14.23),
        "y": 50.00,  "yspan": (41.7, 58.3),      # collapse {41.7, 58.3}
        "color": "#2a78d6", "marker": "o",
        "tx": 14.06, "ty": 66, "ha": "center", "va": "bottom",
    },
    "Single-agent DQN": {
        "x": 13.867, "xci": (13.69, 14.05),
        "y": 16.65,  "yspan": (8.3, 25.0),        # collapse {91.7, 75.0}
        "color": "#1baf7a", "marker": "s",
        "tx": 13.45, "ty": 28, "ha": "right", "va": "center",
    },
    "Independent DQN": {
        "x": 12.601, "xci": (11.30, 13.49),
        "y": 91.65,  "yspan": (83.3, 100.0),      # collapse {0.0, 16.7}
        "color": "#eb6834", "marker": "^",
        "tx": 12.40, "ty": 78, "ha": "center", "va": "top",
    },
}

fig, ax = plt.subplots(figsize=(4.0, 3.1))

# desirable zone: high reward AND robust (top-right) -- the only point in it is AXIOM
zx, zy = 13.35, 40.0
ax.add_patch(Rectangle((zx, zy), 14.9 - zx, 112 - zy, facecolor="#eaf1fb",
                       edgecolor="none", zorder=0))
ax.axvline(zx, color="#9bb6d8", linestyle=(0, (4, 3)), linewidth=0.8, zorder=1)
ax.axhline(zy, color="#9bb6d8", linestyle=(0, (4, 3)), linewidth=0.8, zorder=1)
ax.text(14.85, 106, "accurate\n+ scalable", ha="right", va="top",
        fontsize=8.5, style="italic", color="#3a6aa5", zorder=1)

for name, a in ARMS.items():
    xerr = [[a["x"] - a["xci"][0]], [a["xci"][1] - a["x"]]]
    yerr = [[a["y"] - a["yspan"][0]], [a["yspan"][1] - a["y"]]]
    ax.errorbar(a["x"], a["y"], xerr=xerr, yerr=yerr, fmt=a["marker"],
                color=a["color"], markersize=11, markeredgecolor="white",
                markeredgewidth=0.8, elinewidth=1.1, capsize=3.5,
                capthick=1.0, zorder=5)
    ax.annotate(name, (a["x"], a["y"]), xytext=(a["tx"], a["ty"]),
                ha=a["ha"], va=a["va"], fontsize=9.5,
                color=a["color"], fontweight="bold", zorder=6,
                arrowprops=dict(arrowstyle="-", color=a["color"],
                                lw=0.7, shrinkA=2, shrinkB=8, alpha=0.7))

ax.set_xlim(11.0, 14.95)
ax.set_ylim(-3, 114)
ax.set_xlabel("Mean reward per step, 3 gNBs")
ax.set_ylabel("Collapse resistance, 7 gNBs (%)")
ax.set_title("Only AXIOM is accurate and robust", fontsize=10.5,
             fontweight="bold", pad=6)
ax.set_yticks([0, 20, 40, 60, 80, 100])

out = "../../Papers_4-5/Paper_5/WPC/figures/fig10_axiom_quadrant"
fig.savefig(out + ".pdf", bbox_inches="tight")
fig.savefig(out + ".png", dpi=200, bbox_inches="tight")
print("wrote", out + ".pdf / .png")
