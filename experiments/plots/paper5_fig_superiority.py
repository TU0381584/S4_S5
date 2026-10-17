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

C = {"AXIOM": "#2a78d6", "Single-agent DQN": "#1baf7a", "Independent DQN": "#eb6834", "MAPPO": "#7a4fd0"}
M = {"AXIOM": "o", "Single-agent DQN": "s", "Independent DQN": "^", "MAPPO": "D"}


def draw_quadrant(ax):
    # x: Env A mean reward at 3 gNBs as % of the oracle rule (12.835), CI = reward CI / oracle mean (M65, 30 seeds)
    # y: Env A URLLC/eMBB SLA at 19 gNBs, pooled over 3 layouts x 30 seeds, 95% bootstrap CI (M65)
    arms = {
        "AXIOM": dict(x=98.9, xci=(97.3, 100.2), y=97.3, yspan=(95.2, 99.0), tx=91.0, ty=97.0, ha="right", va="center"),
        "Single-agent DQN": dict(x=96.5, xci=(94.4, 98.4), y=65.3, yspan=(63.0, 67.1), tx=96.5, ty=76.0, ha="center", va="bottom"),
        "Independent DQN": dict(x=90.3, xci=(86.6, 93.7), y=56.4, yspan=(54.0, 58.6), tx=90.3, ty=47.0, ha="center", va="top"),
        "MAPPO": dict(x=78.0, xci=(72.3, 83.7), y=60.6, yspan=(58.6, 62.8), tx=78.0, ty=71.0, ha="center", va="bottom"),
    }
    ax.grid(True, linewidth=0.4, alpha=0.4)
    ax.spines[["top", "right"]].set_visible(False)
    for name, a in arms.items():
        xerr = [[a["x"] - a["xci"][0]], [a["xci"][1] - a["x"]]]
        yerr = [[a["y"] - a["yspan"][0]], [a["yspan"][1] - a["y"]]]
        ax.errorbar(a["x"], a["y"], xerr=xerr, yerr=yerr, fmt=M[name], color=C[name],
                    markersize=10, markeredgecolor="white", markeredgewidth=0.8,
                    elinewidth=1.1, capsize=3.5, capthick=1.0, zorder=5)
        lab = f"{name}\n{a['x']:.1f}%, {a['y']:.1f}%"
        ax.annotate(lab, (a["x"], a["y"]), xytext=(a["tx"], a["ty"]),
                    ha=a["ha"], va=a["va"], fontsize=7.5, color=C[name], fontweight="bold",
                    linespacing=1.2, zorder=6,
                    arrowprops=dict(arrowstyle="-", color=C[name], lw=0.7, shrinkA=2, shrinkB=8, alpha=0.7))
    ax.set_xlim(70, 102)
    ax.set_ylim(40, 102)
    ax.set_xticks([70, 75, 80, 85, 90, 95, 100])
    ax.set_xlabel("Env A reward at 3 gNBs, % of oracle rule")
    ax.set_ylabel("Env A URLLC and eMBB SLA at 19 gNBs (%)")
    ax.set_title("(a) Accuracy against scale, Env A", fontweight="bold")


def draw_radar(ax):
    # all six axes measured (M63); each value is the policy's score divided by the best score on that axis
    # six measured axes (M64/M65); each value is the arm's score over the best learned arm's score
    labels = ["Env A reward\n3 gNBs", "Env B reward\n3 gNBs", "Env A priority\nSLA 7 gNBs", "Env A priority\nSLA 19 gNBs",
              "No collapse\n19 gNBs", "Env B priority\nSLA 7 gNBs"]
    vals = {
        "AXIOM":            [1.000, 1.000, 1.000, 1.000, 0.989, 0.792],
        "Single-agent DQN": [0.976, 0.849, 0.785, 0.671, 0.067, 1.000],
        "Independent DQN":  [0.913, 0.882, 0.768, 0.580, 0.967, 0.903],
        "MAPPO":            [0.789, 0.789, 0.697, 0.623, 1.000, 0.810],
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
    zbase = {"AXIOM": 4, "Independent DQN": 5, "Single-agent DQN": 6, "MAPPO": 5}
    LS = {"AXIOM": (0, (1, 1.35)), "Independent DQN": (0, (5, 2)), "Single-agent DQN": "-", "MAPPO": (0, (3, 1, 1, 1))}
    for name in ["AXIOM", "Independent DQN", "Single-agent DQN", "MAPPO"]:
        v = vals[name] + vals[name][:1]
        lw = 2.2 if name == "AXIOM" else 1.9
        ms = 4 if name == "AXIOM" else 5
        ax.plot(ang, v, color=C[name], linewidth=lw, linestyle=LS[name], marker=M[name],
                markersize=ms, zorder=zbase[name])
        ax.fill(ang, v, color=C[name], alpha=0.16 if name == "AXIOM" else 0.05, zorder=2)
    # raw AXIOM values, placed just inside each vertex so they clear the axis labels
    raw = ["12.70", "8.83", "97%", "97%", "99%", "35%"]
    for a_i, r_i, txt in zip(ang[:-1], vals["AXIOM"], raw):
        ax.text(a_i + 0.2, max(min(r_i, 1.0) - 0.13, 0.13), txt, color=C["AXIOM"], fontsize=6.8,
                fontweight="bold", ha="center", va="center", zorder=7)
    ax.set_title("(b) Capability profile, fraction of best", fontweight="bold", pad=16)
    handles = [Line2D([0], [0], color=C[n], marker=M[n], linewidth=2, linestyle=LS[n], label=n)
               for n in ["AXIOM", "Single-agent DQN", "Independent DQN", "MAPPO"]]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.2),
              ncol=4, frameon=False, fontsize=8, handlelength=1.4, columnspacing=1.2)


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
