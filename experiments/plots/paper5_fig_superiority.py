"""Fig: AXIOM superiority, two panels side by side.
(a) quality-versus-robustness quadrant, (b) capability radar.

Every value is a number reported in the WPC manuscript, recomputed from the logs by m66_verify.py. The radar
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
    "font.size": 8.5, "axes.titlesize": 9, "axes.labelsize": 8.5,
    "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
    "axes.linewidth": 0.7, "pdf.fonttype": 42, "ps.fonttype": 42,
    "savefig.bbox": "tight",
})

C = {"AXIOM": "#2a78d6", "DQN-SA": "#1baf7a", "DQN-I": "#eb6834", "MAPPO": "#7a4fd0"}
M = {"AXIOM": "o", "DQN-SA": "s", "DQN-I": "^", "MAPPO": "D"}


def draw_quadrant(ax):
    # x: Env A mean reward per step at 3 gNBs, 95% bootstrap CI (M65, 30 seeds; m65_n3_view)
    # y: Env A URLLC/eMBB SLA at 37 gNBs (M73), AXIOM pooled over hex 30 + ring 15 + fully-connected 15 runs,
    #    layout-independent baselines over the 30 hex seeds, 95% bootstrap CI
    arms = {
        "AXIOM": dict(x=12.698, xci=(12.490, 12.861), y=93.7, yspan=(89.8, 97.2), tx=11.45, ty=95.0, ha="right", va="center"),
        "DQN-SA": dict(x=12.387, xci=(12.115, 12.630), y=58.7, yspan=(53.5, 62.4), tx=12.387, ty=72.0, ha="center", va="bottom"),
        "DQN-I": dict(x=11.587, xci=(11.112, 12.020), y=32.1, yspan=(25.6, 39.0), tx=10.55, ty=27.0, ha="center", va="center"),
        "MAPPO": dict(x=10.013, xci=(9.298, 10.727), y=56.7, yspan=(51.2, 62.4), tx=10.013, ty=70.0, ha="center", va="bottom"),
    }
    ax.grid(True, linewidth=0.4, alpha=0.4)
    ax.spines[["top", "right"]].set_visible(False)
    for name, a in arms.items():
        xerr = [[a["x"] - a["xci"][0]], [a["xci"][1] - a["x"]]]
        yerr = [[a["y"] - a["yspan"][0]], [a["yspan"][1] - a["y"]]]
        ax.errorbar(a["x"], a["y"], xerr=xerr, yerr=yerr, fmt=M[name], color=C[name],
                    markersize=7, markeredgecolor="white", markeredgewidth=0.6,
                    elinewidth=0.9, capsize=2.5, capthick=1.0, zorder=5)
        lab = f"{name}\n{a['x']:.2f}, {a['y']:.1f}%"
        ax.annotate(lab, (a["x"], a["y"]), xytext=(a["tx"], a["ty"]),
                    ha=a["ha"], va=a["va"], fontsize=8.5, color=C[name], fontweight="bold",
                    linespacing=1.2, zorder=6,
                    arrowprops=dict(arrowstyle="-", color=C[name], lw=0.7, shrinkA=2, shrinkB=8, alpha=0.7))
    ax.set_xlim(9.0, 13.1)
    ax.set_ylim(10, 102)
    ax.set_xticks([9, 10, 11, 12, 13])
    ax.set_xlabel("Env A reward per step at 3 gNBs")
    ax.set_ylabel("Env A priority SLA at 37 gNBs, %")
    


def draw_radar(ax, fig):
    # six measured axes (M64/M65/M73); each value is the arm's score over the best learned arm's score
    labels = ["Env A reward\n3 gNBs", "Env B reward\n3 gNBs", "Env A priority\nSLA 7 gNBs", "Env A priority\nSLA 37 gNBs",
              "No collapse\n37 gNBs", "Env B priority\nSLA 7 gNBs"]
    vals = {
        "AXIOM":            [1.000, 1.000, 1.000, 1.000, 0.900, 0.792],
        "DQN-SA": [0.976, 0.849, 0.785, 0.626, 0.133, 1.000],
        "DQN-I":  [0.913, 0.882, 0.768, 0.343, 0.900, 0.903],
        "MAPPO":            [0.789, 0.789, 0.697, 0.605, 1.000, 0.810],
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
    ax.set_yticklabels([])
    ax.tick_params(axis="x", pad=3)
    for lab_, a_ in zip(ax.get_xticklabels(), ang[:-1]):
        s_ = np.sin(a_)
        lab_.set_horizontalalignment("left" if s_ > 0.1 else "right" if s_ < -0.1 else "center")
    ax.set_rlabel_position(215)
    ax.grid(linewidth=0.4, alpha=0.5)
    # AXIOM first (its fill dominates), baselines on top so their lines stay visible.
    # Distinct dash patterns keep all three readable where the lines overlap.
    zbase = {"AXIOM": 4, "DQN-I": 5, "DQN-SA": 6, "MAPPO": 5}
    LS = {"AXIOM": (0, (1, 1.35)), "DQN-I": (0, (5, 2)), "DQN-SA": "-", "MAPPO": (0, (3, 1, 1, 1))}
    for name in ["AXIOM", "DQN-I", "DQN-SA", "MAPPO"]:
        v = vals[name] + vals[name][:1]
        lw = 1.6 if name == "AXIOM" else 1.3
        ms = 3 if name == "AXIOM" else 3.5
        ax.plot(ang, v, color=C[name], linewidth=lw, linestyle=LS[name], marker=M[name],
                markersize=ms, zorder=zbase[name])
        ax.fill(ang, v, color=C[name], alpha=0.16 if name == "AXIOM" else 0.05, zorder=2)
    
    handles = [Line2D([0], [0], color=C[n], marker=M[n], linewidth=2, linestyle=LS[n], label=n)
               for n in ["AXIOM", "DQN-SA", "DQN-I", "MAPPO"]]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.0),
               ncol=4, frameon=False, fontsize=8.5, handlelength=1.8, columnspacing=1.2)


fig = plt.figure(figsize=(5.16, 2.85))
axL = fig.add_axes([0.1, 0.22, 0.37, 0.72])
axR = fig.add_axes([0.66, 0.27, 0.25, 0.58], projection="polar")
fig.text(0.01, 0.97, "a", fontsize=9, fontweight="bold", va="top")
fig.text(0.52, 0.97, "b", fontsize=9, fontweight="bold", va="top")
draw_quadrant(axL)
draw_radar(axR, fig)

out = "../../Papers_4-5/Paper_5/WPC/figures/fig10_axiom_superiority"
fig.savefig(out + ".pdf", bbox_inches="tight", pad_inches=0.02)
fig.savefig(out + ".png", dpi=200, bbox_inches="tight", pad_inches=0.02)
print("wrote", out + ".pdf / .png")
