"""Fig: per-gNB priority-slice compliance in Env B at nineteen gNBs (hex), AXIOM against the three learned baselines.

Each hexagon is one gNB at its true position, coloured by the share of evaluation steps on which that gNB meets
both the URLLC and the eMBB SLA under the framework's own per-gNB test (the mean of the two compliances), averaged
over the 15 reported seeds of M75 D. The centre gNB has six coupled neighbours and the highest offered load, since
the simulator pins its load multiplier at 1.0 while the others draw theirs from [0.9, 1.0]. The same
quantities on the 15 fresh seeds of M80 D are written to the summary as a replication. Every plotted number is in
<out>_summary.json, which m66_verify checks.
"""
import json
import sys

import numpy as np
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/scripts")
sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/plots")
sys.path.insert(0, "/home/kmanojp/oranslice_rig/framework")
from paper5_common import MAIN_WIDTH_IN  # noqa: E402
from qoe_oran_framework.marl.topology import hex_cluster_coords  # noqa: E402
import m6_run_experiment as m6  # noqa: E402

RES = "/home/kmanojp/oranslice_rig/experiments/results"
SETS = {"reported": ("m75/D_envB_n19_hex", list(range(900, 912)) + [1000, 1001, 1002]),
        "fresh": ("m80/D_envB_n19_hex_fresh", list(range(7000, 7015)))}
ARMS = [("axiom2", "AXIOM (proposed)"), ("mappo_tuned", "MAPPO"), ("single_agent_dqn", "DQN-SA"), ("independent_dqn", "DQN-I")]
TAG = dict(fc="#f4ead6", ec="#9c7a45", tc="#4f3a15")
# inferno, trimmed at both ends so the darkest cells keep their outlines and the palest stay off white;
# its lightness rises steadily, so it reads in greyscale and for protan, deutan, and tritan readers
CMAP = mpl.colors.ListedColormap(plt.get_cmap("inferno")(np.linspace(0.08, 0.92, 256)), name="inferno_trim")
VMIN, VMAX = 50, 85


def per_gnb(cell, arm, seeds):
    acc = np.zeros(19)
    for s in seeds:
        d = json.load(open(f"{RES}/{cell}/{arm}/seed{s}/eval/per_gnb_sla.json"))
        idx = [int(g.split("-")[1]) for g in d["gnbs"]]
        v = np.zeros(19)
        v[idx] = 50 * (np.array(d["per_gnb_compliance"]["urllc"]) + np.array(d["per_gnb_compliance"]["embb"]))
        acc += v
    return acc / len(seeds)


def hexagon(cx, cy, r):
    return [(cx + r * np.cos(np.radians(30 + 60 * k)), cy + r * np.sin(np.radians(30 + 60 * k))) for k in range(6)]


def main():
    out = "../../Papers_4-5/Paper_5/WPC/figures/fig_pergnb_envb"
    coords = hex_cluster_coords(19)
    adj = np.asarray(m6.adjacency_for("hex", 19)) > 0
    deg = adj.sum(1) - np.diag(adj)
    interior = deg == 6
    summary = {"degree": deg.tolist(), "sets": {}}
    for name, (cell, seeds) in SETS.items():
        summary["sets"][name] = {"cell": cell, "seeds": seeds, "arms": {}}
        for arm, _ in ARMS + [("rule_static", ""), ("rule_local_transfer", "")]:
            v = per_gnb(cell, arm, seeds)
            summary["sets"][name]["arms"][arm] = {"per_gnb": v.round(4).tolist(), "centre": float(v[0]), "others": float(v[1:].mean()),
                                                  "inner_ring": float(v[1:7].mean()), "edge": float(v[~interior].mean()),
                                                  "min": float(v.min()), "max": float(v.max())}
    fig = plt.figure(figsize=(MAIN_WIDTH_IN, 2.25))
    w = 0.225
    for k, (arm, label) in enumerate(ARMS):
        ax = fig.add_axes([0.005 + k * 0.248, 0.19, w, 0.56])
        v = summary["sets"]["reported"]["arms"][arm]["per_gnb"]
        for g, ((q, rr), val) in enumerate(zip(coords, v)):
            cx, cy = np.sqrt(3) * (q + rr / 2), -1.5 * rr
            ax.add_patch(Polygon(hexagon(cx, cy, 0.97), closed=True, facecolor=CMAP((val - VMIN) / (VMAX - VMIN)),
                                 edgecolor="#222222" if g == 0 else "white", linewidth=1.6 if g == 0 else 0.6, zorder=3 if g == 0 else 2))
        ax.set_aspect("equal")
        ax.autoscale_view()
        ax.axis("off")
        s = summary["sets"]["reported"]["arms"][arm]
        ax.set_title(label, fontsize=8.5, color="#0072B2" if arm == "axiom2" else "#222222", pad=24)
        ax.text(0.5, 1.0, f"centre {s['centre']:.1f}%\nothers {s['others']:.1f}%", transform=ax.transAxes,
                ha="center", va="bottom", fontsize=8, linespacing=1.1)
        fig.text(0.005 + k * 0.248, 0.995, "abcd"[k], fontsize=9, va="top")
        fig.text(0.035 + k * 0.248, 0.997, "Env B", fontsize=8.5, va="top", color=TAG["tc"],
                 bbox=dict(boxstyle="round,pad=0.25", fc=TAG["fc"], ec=TAG["ec"], lw=0.6))
    cax = fig.add_axes([0.3, 0.1, 0.4, 0.045])
    cb = mpl.colorbar.ColorbarBase(cax, cmap=CMAP, norm=mpl.colors.Normalize(VMIN, VMAX), orientation="horizontal")
    cb.ax.tick_params(labelsize=8, length=2)
    cb.set_label("Per-gNB priority-slice SLA, %, the centre gNB outlined", fontsize=8)
    fig.savefig(out + ".pdf", bbox_inches="tight", pad_inches=0.04)
    fig.savefig(out + ".png", dpi=200, bbox_inches="tight", pad_inches=0.04)
    json.dump(summary, open(out + "_summary.json", "w"), indent=1)
    for name in SETS:
        for arm, s in summary["sets"][name]["arms"].items():
            print(name, arm, f"centre {s['centre']:.2f} others {s['others']:.2f} inner {s['inner_ring']:.2f} edge {s['edge']:.2f}")


if __name__ == "__main__":
    main()
