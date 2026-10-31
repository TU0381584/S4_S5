#!/usr/bin/env python3
"""Multi-gNB decision map: what each learned policy does at every gNB of the
19-gNB hex cluster in Env A, or of the 37-gNB cluster (M73) with --n 37.

Each hexagon is one gNB, placed at its true axial position in the simulator's
hex layout (qoe_oran_framework.marl.topology.hex_cluster_coords). It is split
into three rhombi, one per slice. A rhombus is coloured by how correct that
gNB's admission gate is for the slice, averaged over every evaluation step of
every seed. The gate of a (gNB, slice) pair is the PRB-ratio ceiling that each
accept raises and each reject lowers (action_mapping.AdmissionGate), scaled to
openness in [0, 1] between the slice's floor and cap. Correct behaviour under
the shared budget is to keep URLLC and eMBB open and to shed mMTC, so
correctness is the openness for URLLC and eMBB and one minus it for mMTC.

Every plotted number is written to <out>_summary.json.

Usage: paper5_fig_gnb_map.py --cell m65_scaling/n19_hex --out Papers_4-5/Paper_5/WPC/figures/fig13_gnb_map
       paper5_fig_gnb_map.py --n 37 --cell m73/A_n37_hex --out Papers_4-5/Paper_5/WPC/figures/fig13_gnb_map
At 37 gNBs the hex layout comes from m73_run.py's extension of the framework's
ring walk, and every arm, including the layout-independent baselines, is read
from the M73 hex cell.
"""
import argparse
import gzip
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import PolyCollection
from matplotlib.patches import Polygon, RegularPolygon

sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/scripts")
sys.path.insert(0, "/home/kmanojp/oranslice_rig/framework")
from m66_verify import S30_19, find_eval, prio, seeds_of  # noqa: E402
from qoe_oran_framework.marl.topology import hex_cluster_coords  # noqa: E402

SLICES = ("urllc", "embb", "mmtc")
FLOOR_CAP = {"urllc": (5, 33), "embb": (10, 66), "mmtc": (5, 11)}   # saclb_offline_dqn_n19.yaml and _n37.yaml
ARMS = [("axiom2", "AXIOM (proposed)"), ("single_agent_dqn", "DQN-SA"),
        ("independent_dqn", "DQN-I"), ("mappo_tuned", "MAPPO")]
CMAP = plt.get_cmap("RdYlBu")


def gate_openness(path, n):
    acc, cnt = np.zeros((n, 3)), 0
    with (gzip.open(path, "rt") if path.endswith(".gz") else open(path)) as fh:
        for line in fh:
            ev = json.loads(line).get("evidence")
            if not isinstance(ev, dict) or ev.get("rollup") or "ceilings" not in ev:
                continue
            for key, c in ev["ceilings"].items():
                g, sl = key.split(":")
                lo, hi = FLOOR_CAP[sl]
                acc[int(g.split("-")[1]), SLICES.index(sl)] += (c["max_ratio"] - lo) / (hi - lo)
            cnt += 1
    return acc / cnt


def hex_vertices(cx, cy, r):
    # pointy-top hexagon, vertices at 30 + 60k degrees
    return [(cx + r * np.cos(np.radians(30 + 60 * k)), cy + r * np.sin(np.radians(30 + 60 * k))) for k in range(6)]


def rhombi(cx, cy, r):
    v = hex_vertices(cx, cy, r)
    c = (cx, cy)
    # top rhombus (URLLC), lower-left (eMBB), lower-right (mMTC)
    return [[c, v[0], v[1], v[2]], [c, v[2], v[3], v[4]], [c, v[4], v[5], v[0]]]


def draw_cluster(ax, coords, corr, r=0.93, lw=0.6):
    polys, cols = [], []
    for (q, rr), row in zip(coords, corr):
        cx, cy = np.sqrt(3) * (q + rr / 2), -1.5 * rr
        for poly, val in zip(rhombi(cx, cy, r), row):
            polys.append(poly)
            cols.append(CMAP(val))
    ax.add_collection(PolyCollection(polys, facecolors=cols, edgecolors="white", linewidths=lw))
    for (q, rr) in coords:
        cx, cy = np.sqrt(3) * (q + rr / 2), -1.5 * rr
        ax.add_patch(Polygon(hex_vertices(cx, cy, r), closed=True, fill=False, edgecolor="#4a4a4a", linewidth=0.7))
    ax.set_aspect("equal")
    ax.autoscale_view()
    ax.axis("off")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cell", default="m65_scaling/n19_hex")
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=19, choices=[19, 37])
    a = ap.parse_args()
    n = a.n
    if n == 37:
        import m73_run
        m73_run.install()
        coords = m73_run.hex_cluster_coords(37)
    else:
        coords = hex_cluster_coords(n)
    summary = {"cell": a.cell, "n_gnbs": n, "seeds": S30_19, "arms": {}}
    # drawn at the main text's printed width (372 pt) so every label prints at 8 pt or more; the four panels,
    # the key and the colour bar sit symmetrically, so the figure centres on the page
    fig = plt.figure(figsize=(372.0 / 72.27, 2.3))
    L, W, G = 0.02, 0.225, (0.96 - 4 * 0.225) / 3
    for idx, (arm, label) in enumerate(ARMS):
        mats = [gate_openness(p, n) for s in S30_19 if (p := find_eval(a.cell, arm, s))]
        op = np.mean(mats, axis=0)
        corr = op.copy()
        corr[:, 2] = 1 - op[:, 2]
        rows = seeds_of(a.cell, arm, S30_19)
        p_sla = 100 * float(np.mean([prio(r) for r in rows.values()]))
        coll = int(sum(r["collapsed"] for r in rows.values()))
        summary["arms"][arm] = {"n_seeds": len(mats), "openness_per_gnb": op.round(4).tolist(),
                                "correctness_per_gnb": corr.round(4).tolist(),
                                "mean_openness": dict(zip(SLICES, op.mean(axis=0).round(4).tolist())),
                                "priority_sla_pct": round(p_sla, 2), "collapsed_seeds": coll, "n_eval_seeds": len(rows)}
        ax = fig.add_axes([L + idx * (W + G), 0.27, W, 0.47])
        if idx == 0:
            ax0 = ax
        draw_cluster(ax, coords, corr, lw=0.3)
        emph = arm == "axiom2"
        col = "#1f5fae" if emph else "#333333"
        ax.annotate(f"Priority SLA {p_sla:.1f}%\n{coll}/{len(rows)} collapsed", xy=(0.5, 1), xycoords="axes fraction",
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8, linespacing=1.1, color=col)
        ax.annotate(label, xy=(0.5, 1), xycoords="axes fraction", xytext=(0, 24), textcoords="offset points",
                    ha="center", va="bottom", fontsize=8.5, color=col)
        if emph:
            ax.axis("on")
            ax.set_xticks([]); ax.set_yticks([])
            for sp in ax.spines.values():
                sp.set_edgecolor("#1f5fae"); sp.set_linewidth(1.4)
    # boxed environment tag in the style of paper5_common.ENV_TAG (not imported: its rcParams would restyle this figure)
    # it sits above the first panel's title with a clear gap, aligned with that panel's left edge
    ax0.annotate("Env A", xy=(0, 1), xycoords="axes fraction", xytext=(0, 44), textcoords="offset points", ha="left", va="bottom",
                 fontsize=8.5, color="#26344a", annotation_clip=False,
                 bbox=dict(boxstyle="round,pad=0.25", fc="#e2e8f0", ec="#5a6b82", lw=0.6))
    # key: one gNB's hexagon under the first two panels, its three slice rhombi labelled to its right
    kax = fig.add_axes([L, 0.0, 2 * W + G, 0.21])
    draw_cluster(kax, [(0, 0)], np.array([[1.0, 1.0, 1.0]]), r=1.0, lw=0.8)
    # the eMBB leader runs under the hexagon so that it crosses no other gate
    for (x0, y0, y1, txt, cs) in ((0, 0.55, 0.95, "URLLC gate, correct if open", "arc3"),
                                  (0.45, -0.3, 0.0, "mMTC gate, correct if shed", "arc3"),
                                  (-0.3, -0.7, -1.12, "eMBB gate, correct if open", "angle,angleA=0,angleB=90,rad=0")):
        kax.annotate(txt, xy=(x0, y0), xytext=(1.9, y1), fontsize=8, ha="left", va="center",
                     arrowprops=dict(arrowstyle="-", color="#555555", lw=0.6, connectionstyle=cs, shrinkA=1, shrinkB=0))
    kax.text(-1.3, 0, "One gNB", fontsize=8, ha="right", va="center")
    kax.set_xlim(-4.6, 13.0); kax.set_ylim(-1.3, 1.15)
    # colour bar under the last two panels
    cax = fig.add_axes([L + 2 * (W + G) + 0.04, 0.12, 2 * W + G - 0.08, 0.045])
    cb = fig.colorbar(plt.cm.ScalarMappable(cmap=CMAP, norm=plt.Normalize(0, 1)), cax=cax, orientation="horizontal")
    cb.set_ticks([0, 0.5, 1]); cb.set_ticklabels(["wrong", "partial", "correct"]); cb.ax.tick_params(labelsize=8, length=2)
    cb.set_label("Gate correctness, mean of 30 seeds", fontsize=8)
    fig.savefig(a.out + ".pdf", bbox_inches="tight")
    fig.savefig(a.out + ".png", dpi=200, bbox_inches="tight")
    json.dump(summary, open(a.out + "_summary.json", "w"), indent=1)
    for arm, v in summary["arms"].items():
        print(arm, v["mean_openness"], v["priority_sla_pct"], v["collapsed_seeds"], v["n_seeds"])


if __name__ == "__main__":
    main()
