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
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import PolyCollection
from matplotlib.patches import Polygon, RegularPolygon

sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/scripts")
sys.path.insert(0, "/home/kmanojp/oranslice_rig/framework")
from m66_verify import S30_19, find_eval, pooled_paths, prio, seeds_of  # noqa: E402
from qoe_oran_framework.marl.topology import hex_cluster_coords  # noqa: E402

SLICES = ("urllc", "embb", "mmtc")
FLOOR_CAP = {"urllc": (5, 33), "embb": (10, 66), "mmtc": (5, 11)}   # saclb_offline_dqn_n19.yaml and _n37.yaml
ARMS = [("axiom2", "AXIOM"), ("mappo_tuned", "MAPPO"), ("single_agent_dqn", "DQN-SA"), ("independent_dqn", "DQN-I")]
MAIN_WIDTH_IN = 119.0 / 25.4  # WPC maximum figure width
# cividis on 0 to 1 (figure audit): lightness rises steadily, so it reads in greyscale and for colour-vision deficiencies
# inferno restored (2026-11-09), trimmed at both ends as before; its lightness rises steadily, so it is CVD-safe
CMAP = mpl.colors.ListedColormap(plt.get_cmap("inferno")(np.linspace(0.08, 0.92, 256)), name="inferno_trim")
sys.path.insert(0, "/home/kmanojp/oranslice_rig/Papers_4-5/Paper_5/WPC/figures")
import axiom_style as S  # noqa: E402
S.setup()


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
    # flat-topped hexagon, vertices at 60k degrees (figure audit)
    return [(cx + r * np.cos(np.radians(60 * k)), cy + r * np.sin(np.radians(60 * k))) for k in range(6)]


def rhombi(cx, cy, r):
    v = hex_vertices(cx, cy, r)
    c = (cx, cy)
    # three sectors: upper (URLLC, 0 to 120 degrees), left (eMBB, 120 to 240), lower right (mMTC, 240 to 360)
    return [[c, v[0], v[1], v[2]], [c, v[2], v[3], v[4]], [c, v[4], v[5], v[0]]]


def centre(q, rr):
    # axial coordinates to centres for flat-topped hexagons
    return 1.5 * q, np.sqrt(3) * (rr + q / 2)


def draw_cluster(ax, coords, corr, r=0.93, lw=0.6):
    polys, cols = [], []
    for (q, rr), row in zip(coords, corr):
        cx, cy = centre(q, rr)
        for poly, val in zip(rhombi(cx, cy, r), row):
            polys.append(poly)
            cols.append(CMAP(val))
    ax.add_collection(PolyCollection(polys, facecolors=cols, edgecolors="white", linewidths=lw))
    for (q, rr) in coords:
        cx, cy = centre(q, rr)
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
    H = 66.0   # one row of four clusters (2026-11-10, author request), key and colour bar side by side below
    fig = S.figure("full", H)
    fw, fh = (lambda mm: mm / 119.0), (lambda mm: mm / H)
    slots = [(1.0, 19.5), (30.5, 19.5), (60.0, 19.5), (89.5, 19.5)]   # each header on three short lines at 8 pt
    for idx, (arm, label) in enumerate(ARMS):
        mats = [gate_openness(p, n) for s, p in pooled_paths(a.cell, arm, S30_19)]   # pooled with M107 seeds where the cell is pooled
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
        x0_, y0_ = slots[idx]
        ax = fig.add_axes([fw(x0_), fh(y0_), fw(28.5), fh(28.5)])
        draw_cluster(ax, coords, corr, lw=0.3)
        col = S.POLICY[arm]["color"] if arm == "axiom2" else S.INK
        if arm == "axiom2":   # AXIOM's panel framed in its colour, as before
            ax.axis("on"); ax.set_xticks([]); ax.set_yticks([])
            for sp in ax.spines.values():
                sp.set_visible(True); sp.set_edgecolor(col); sp.set_linewidth(1.2)
        ax.text(0.5, 1.03, f"{label}\nSLA {p_sla:.1f}%\ncollapsed {coll}/{len(rows)}", transform=ax.transAxes,
                ha="center", va="bottom", color=col, linespacing=1.1)
    S.env_badge(fig, fw(1), fh(H - 1.0), "A", va="top")   # pre-audit badge (restored 2026-11-09)
    # key: one gNB's hexagon, its three slice sectors labelled (left half of the bottom row)
    kax = fig.add_axes([fw(0), fh(0.5), fw(62), fh(16)])
    draw_cluster(kax, [(0, 0)], np.array([[1.0, 1.0, 1.0]]), r=1.0, lw=0.8)
    for (x0, y0, y1, txt) in ((0.35, 0.55, 0.85, "URLLC gate,\ncorrect if open"), (0.4, -0.45, -0.85, "mMTC gate,\ncorrect if shed")):
        kax.annotate(txt, xy=(x0, y0), xytext=(1.7, y1), ha="left", va="center", linespacing=1.0,
                     arrowprops=dict(arrowstyle="-", color="#555555", lw=0.6, shrinkA=1, shrinkB=0))
    kax.annotate("eMBB gate,\ncorrect if open", xy=(-0.55, 0.0), xytext=(-1.5, 0.0), ha="right", va="center", linespacing=1.0,
                 arrowprops=dict(arrowstyle="-", color="#555555", lw=0.6, shrinkA=1, shrinkB=0))
    kax.set_xlim(-6.2, 6.2); kax.set_ylim(-1.6, 1.6)
    # shared colour bar (right half of the bottom row)
    cax = fig.add_axes([fw(68), fh(11.5), fw(46), fh(2.2)])
    cb = fig.colorbar(plt.cm.ScalarMappable(cmap=CMAP, norm=plt.Normalize(0, 1)), cax=cax, orientation="horizontal")
    cb.set_ticks([0, 0.5, 1]); cb.set_ticklabels(["wrong", "partial", "correct"]); cb.ax.tick_params(length=2)
    cb.outline.set_linewidth(0.5)
    ns_ = {v["n_seeds"] for v in summary["arms"].values()}
    assert len(ns_) == 1, ns_
    cb.set_label(f"Gate correctness, mean of {ns_.pop()} seeds")
    print(S.save(fig, a.out))
    json.dump(summary, open(a.out + "_summary.json", "w"), indent=1)
    for arm, v in summary["arms"].items():
        print(arm, v["mean_openness"], v["priority_sla_pct"], v["collapsed_seeds"], v["n_seeds"])


if __name__ == "__main__":
    main()
