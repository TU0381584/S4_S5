"""Fig: AXIOM superiority, two panels side by side.
(a) quality-versus-robustness quadrant, (b) capability radar.

Every value is a number already reported in the WPC manuscript. The radar
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
    arms = {
        "AXIOM": dict(x=14.062, xci=(13.91, 14.23), y=50.00, yspan=(41.7, 58.3),
                      tx=14.15, ty=70, ha="center", va="bottom"),
        "Single-agent DQN": dict(x=13.867, xci=(13.69, 14.05), y=16.65, yspan=(8.3, 25.0),
                                 tx=13.45, ty=29, ha="right", va="center"),
        "Independent DQN": dict(x=12.601, xci=(11.30, 13.49), y=91.65, yspan=(83.3, 100.0),
                                tx=12.25, ty=82, ha="center", va="top"),
    }
    ax.grid(True, linewidth=0.4, alpha=0.4)
    ax.spines[["top", "right"]].set_visible(False)
    zx, zy = 13.35, 40.0
    ax.add_patch(Rectangle((zx, zy), 14.9 - zx, 112 - zy, facecolor="#eaf1fb",
                           edgecolor="none", zorder=0))
    ax.axvline(zx, color="#9bb6d8", linestyle=(0, (4, 3)), linewidth=0.8, zorder=1)
    ax.axhline(zy, color="#9bb6d8", linestyle=(0, (4, 3)), linewidth=0.8, zorder=1)
    ax.text(14.85, 106, "accurate\n+ scalable", ha="right", va="top",
            fontsize=8.5, style="italic", color="#3a6aa5", zorder=1)
    for name, a in arms.items():
        xerr = [[a["x"] - a["xci"][0]], [a["xci"][1] - a["x"]]]
        yerr = [[a["y"] - a["yspan"][0]], [a["yspan"][1] - a["y"]]]
        ax.errorbar(a["x"], a["y"], xerr=xerr, yerr=yerr, fmt=M[name], color=C[name],
                    markersize=11, markeredgecolor="white", markeredgewidth=0.8,
                    elinewidth=1.1, capsize=3.5, capthick=1.0, zorder=5)
        lab = f"{name}\n{a['x']:.2f}, {a['y']:.0f}%"
        ax.annotate(lab, (a["x"], a["y"]), xytext=(a["tx"], a["ty"]),
                    ha=a["ha"], va=a["va"], fontsize=8, color=C[name], fontweight="bold",
                    linespacing=1.25, zorder=6,
                    arrowprops=dict(arrowstyle="-", color=C[name], lw=0.7,
                                    shrinkA=2, shrinkB=8, alpha=0.7))
    ax.set_xlim(11.0, 14.95)
    ax.set_ylim(-3, 116)
    ax.set_xlabel("Mean reward per step, 3 gNBs")
    ax.set_ylabel("Collapse resistance, 7 gNBs (%)")
    ax.set_title("(a) Only AXIOM is accurate and robust", fontweight="bold")
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.text(11.1, 111, "reward over 30 seeds; collapse over 2$\\times$12 seeds",
            fontsize=6.5, style="italic", color="#666", va="top")


def draw_radar(ax):
    labels = ["Reward", "Blocking\naccuracy", "Scale\nrobustness", "Topology\naware", "Privacy\nready"]
    vals = {
        "AXIOM":            [1.000, 0.964, 0.546, 1.0, 1.0],
        "Single-agent DQN": [0.986, 1.000, 0.182, 0.0, 0.0],
        "Independent DQN":  [0.896, 0.913, 1.000, 0.0, 0.0],
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
    ax.tick_params(axis="x", pad=6)
    ax.grid(linewidth=0.4, alpha=0.5)
    for name in ["Single-agent DQN", "Independent DQN", "AXIOM"]:
        v = vals[name] + vals[name][:1]
        lw = 2.0 if name == "AXIOM" else 1.3
        ax.plot(ang, v, color=C[name], linewidth=lw, marker=M[name], markersize=4, zorder=4)
        ax.fill(ang, v, color=C[name], alpha=0.16 if name == "AXIOM" else 0.08, zorder=2)
    # raw AXIOM values, placed just inside each vertex so they clear the axis labels
    raw = ["14.06", "0.95", "50%", "yes", "yes"]
    for a_i, r_i, txt in zip(ang[:-1], vals["AXIOM"], raw):
        ax.text(a_i, max(min(r_i, 1.0) - 0.15, 0.13), txt, color=C["AXIOM"], fontsize=6.8,
                fontweight="bold", ha="center", va="center", zorder=7)
    ax.set_title("(b) Capability profile, fraction of best", fontweight="bold", pad=16)
    handles = [Line2D([0], [0], color=C[n], marker=M[n], linewidth=2, label=n)
               for n in ["AXIOM", "Single-agent DQN", "Independent DQN"]]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.09),
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
