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
    fig = plt.figure(figsize=(7.4, 2.75))
    gs = fig.add_gridspec(2, 4, height_ratios=[1, 0.27], hspace=0.06, wspace=0.08)
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
        ax = fig.add_subplot(gs[0, idx])
        draw_cluster(ax, coords, corr, lw=0.4)
        emph = arm == "axiom2"
        col = "#1f5fae" if emph else "#333333"
        ax.set_title(label, fontsize=9.5 if emph else 9, fontweight="normal", color=col, pad=19)
        ax.text(0.5, 1.01, f"Priority SLA {p_sla:.1f}%\n{coll}/{len(rows)} seeds collapsed",
                transform=ax.transAxes, ha="center", va="bottom", fontsize=7.2, linespacing=1.15,
                fontweight="normal", color=col)
        if emph:
            ax.axis("on")
            ax.set_xticks([]); ax.set_yticks([])
            for sp in ax.spines.values():
                sp.set_edgecolor("#1f5fae"); sp.set_linewidth(1.8)
    # key: one hexagon with its three slice rhombi labelled beside it
    kax = fig.add_subplot(gs[1, 0:2])
    draw_cluster(kax, [(0, 0)], np.array([[1.0, 1.0, 1.0]]), r=1.0, lw=1.0)
    for (x0, y0, x1, y1, txt, ha) in ((0, 0.55, -1.5, 0.7, "URLLC gate, correct if open", "right"),
                                      (-0.45, -0.3, -1.5, -0.7, "eMBB gate, correct if open", "right"),
                                      (0.45, -0.3, 1.5, -0.7, "mMTC gate, correct if shed", "left")):
        kax.annotate(txt, xy=(x0, y0), xytext=(x1, y1), fontsize=7, ha=ha, va="center",
                     arrowprops=dict(arrowstyle="-", color="#555555", lw=0.6))
    kax.text(1.5, 0.7, "One gNB", fontsize=7.5, ha="left", va="center")
    kax.set_xlim(-9.5, 9.5); kax.set_ylim(-1.15, 1.15)
    cax = fig.add_subplot(gs[1, 2:4])
    pos = cax.get_position()
    cax.set_position([pos.x0 + 0.05, pos.y0 + pos.height * 0.55, pos.width - 0.1, pos.height * 0.22])
    cb = fig.colorbar(plt.cm.ScalarMappable(cmap=CMAP, norm=plt.Normalize(0, 1)), cax=cax, orientation="horizontal")
    cb.set_ticks([0, 0.5, 1]); cb.set_ticklabels(["wrong", "partial", "correct"]); cb.ax.tick_params(labelsize=7, length=2)
    cb.set_label("Gate correctness, mean over 30 seeds and every evaluation step", fontsize=7)
    fig.savefig(a.out + ".pdf", bbox_inches="tight")
    fig.savefig(a.out + ".png", dpi=200, bbox_inches="tight")
    json.dump(summary, open(a.out + "_summary.json", "w"), indent=1)
    for arm, v in summary["arms"].items():
        print(arm, v["mean_openness"], v["priority_sla_pct"], v["collapsed_seeds"], v["n_seeds"])


if __name__ == "__main__":
    main()
