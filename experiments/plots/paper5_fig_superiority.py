"""Fig: AXIOM superiority, two panels side by side.
(a) quality-versus-robustness quadrant, (b) capability radar.

Every value is a number already reported in the WPC manuscript (M63 rerun). The radar
normalises each axis as a fraction of the best policy on that axis, so a
baseline reads 0 only where it genuinely has no such capability, namely the
topology and privacy axes. Colours/markers match the other result figures.
"""
import numpy as np
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D

mpl.rcParams.update({
    "font.size": 9.5, "axes.titlesize": 10.5, "axes.labelsize": 9.5,
    "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
    "axes.linewidth": 0.7, "pdf.fonttype": 42, "ps.fonttype": 42,
    "savefig.bbox": "tight",
})

C = {"AXIOM": "#2a78d6", "Single-agent DQN": "#1baf7a", "Independent DQN": "#eb6834"}
M = {"AXIOM": "o", "Single-agent DQN": "s", "Independent DQN": "^"}


def draw_quadrant(ax):
    # x: mean reward at 3 gNBs as % of the oracle rule (12.835), CI = reward CI / oracle mean (M63 base, 30 seeds)
    # y: URLLC/eMBB SLA compliance at 19 gNBs, pooled over 3 layouts x 15 seeds, 95% bootstrap CI (M63 scaling)
    arms = {
        "AXIOM": dict(x=100.0, xci=(99.5, 100.5), y=79.1, yspan=(73.8, 84.3),
                      tx=96.3, ty=86.5, ha="center", va="center"),
        "Single-agent DQN": dict(x=96.5, xci=(94.4, 98.4), y=65.9, yspan=(65.2, 66.5),
                                 tx=93.2, ty=74.5, ha="center", va="bottom"),
        "Independent DQN": dict(x=90.3, xci=(86.6, 93.7), y=54.4, yspan=(50.9, 58.0),
                                tx=90.3, ty=44.0, ha="center", va="top"),
    }
    ax.grid(True, linewidth=0.4, alpha=0.4)
    ax.spines[["top", "right"]].set_visible(False)
    for name, a in arms.items():
        xerr = [[a["x"] - a["xci"][0]], [a["xci"][1] - a["x"]]]
        yerr = [[a["y"] - a["yspan"][0]], [a["yspan"][1] - a["y"]]]
        ax.errorbar(a["x"], a["y"], xerr=xerr, yerr=yerr, fmt=M[name], color=C[name],
                    markersize=11, markeredgecolor="white", markeredgewidth=0.8,
                    elinewidth=1.1, capsize=3.5, capthick=1.0, zorder=5)
        lab = f"{name}\n{a['x']:.1f}%, {a['y']:.1f}%"
        ax.annotate(lab, (a["x"], a["y"]), xytext=(a["tx"], a["ty"]),
                    ha=a["ha"], va=a["va"], fontsize=8, color=C[name], fontweight="bold",
                    linespacing=1.25, zorder=6,
                    arrowprops=dict(arrowstyle="-", color=C[name], lw=0.7,
                                    shrinkA=2, shrinkB=8, alpha=0.7))
    ax.set_xlim(85, 102)
    ax.set_ylim(38, 92)
    ax.set_xlabel("Reward at 3 gNBs, % of oracle rule")
    ax.set_ylabel("URLLC and eMBB SLA at 19 gNBs (%)")
    ax.set_title("(a) Accuracy against scale", fontweight="bold")
    ax.set_xticks([86, 90, 94, 98, 102])


def draw_radar(ax):
    # all six axes measured (M63); each value is the policy's score divided by the best score on that axis
    labels = ["Reward\n3 gNBs", "Blocking\naccuracy", "Priority SLA\n7 gNBs", "Priority SLA\n19 gNBs",
              "No collapse\n19 gNBs", "Reward\n19 gNBs"]
    vals = {
        "AXIOM":            [1.000, 1.000, 1.000, 1.000, 0.933, 1.000],
        "Single-agent DQN": [0.965, 0.990, 0.784, 0.833, 0.022, 0.953],
        "Independent DQN":  [0.903, 0.962, 0.767, 0.688, 1.000, 0.925],
    }
    N = len(labels)
    ang = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    ang += ang[:1]
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(ang[:-1])
    ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_ylim(0, 1.08)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0.25", "0.5", "0.75", "1.0"], fontsize=6.5, color="#999")
    ax.tick_params(axis="x", pad=13)
    ax.set_rlabel_position(215)
    ax.grid(linewidth=0.4, alpha=0.5)
    # AXIOM first (its fill dominates), baselines on top so their lines stay visible.
    # Distinct dash patterns keep all three readable where the lines overlap.
    zbase = {"AXIOM": 4, "Independent DQN": 5, "Single-agent DQN": 6}
    LS = {"AXIOM": (0, (1, 1.35)), "Independent DQN": (0, (5, 2)), "Single-agent DQN": "-"}
    for name in ["AXIOM", "Independent DQN", "Single-agent DQN"]:
        v = vals[name] + vals[name][:1]
        lw = 2.2 if name == "AXIOM" else 1.9
        ms = 4 if name == "AXIOM" else 5
        ax.plot(ang, v, color=C[name], linewidth=lw, linestyle=LS[name], marker=M[name],
                markersize=ms, zorder=zbase[name])
        ax.fill(ang, v, color=C[name], alpha=0.16 if name == "AXIOM" else 0.05, zorder=2)
    # raw AXIOM values, placed just inside each vertex so they clear the axis labels
    raw = ["12.83", "1.00", "97%", "79%", "93%", "82.4"]
    for a_i, r_i, txt in zip(ang[:-1], vals["AXIOM"], raw):
        ax.text(a_i + 0.2, max(min(r_i, 1.0) - 0.13, 0.13), txt, color=C["AXIOM"], fontsize=6.8,
                fontweight="bold", ha="center", va="center", zorder=7)
    ax.set_title("(b) Capability profile, fraction of best", fontweight="bold", pad=16)
    handles = [Line2D([0], [0], color=C[n], marker=M[n], linewidth=2, linestyle=LS[n], label=n)
               for n in ["AXIOM", "Single-agent DQN", "Independent DQN"]]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.2),
              ncol=3, frameon=False, fontsize=8, handlelength=1.4, columnspacing=1.2)


fig = plt.figure(figsize=(8.8, 3.25))
axL = fig.add_subplot(1, 2, 1)
axR = fig.add_subplot(1, 2, 2, projection="polar")
draw_quadrant(axL)
draw_radar(axR)
fig.subplots_adjust(wspace=0.38, bottom=0.14)

out = "../../Papers_4-5/Paper_5/WPC/figures/fig10_axiom_superiority"
fig.savefig(out + ".pdf", bbox_inches="tight")
fig.savefig(out + ".png", dpi=200, bbox_inches="tight")
print("wrote", out + ".pdf / .png")
