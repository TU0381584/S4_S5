#!/usr/bin/env python3
"""Main-paper learning curves (Gate 3 item 2): training reward per gNB per step in each of the 300 training
episodes, mean over seeds with a 95% bootstrap percentile band, for the four learned policies.
Panels: Env A at 3, 19 (hex) and 37 (hex) gNBs, Env B at 3 and 7 (ring) gNBs. Data: experiments/results/gate3/curves.json,
extracted from the stored training logs by experiments/scripts/gate3_reanalysis.py (no run is repeated).
Training rewards include exploration, so they sit below the evaluation rewards of the tables.
Bands are solid tints, since EPS has no transparency. Every plotted number goes to <out>_summary.json.
Usage (from experiments/plots): python paper5_fig_learning.py
"""
import json, os, sys
import numpy as np
sys.path.insert(0, "/home/kmanojp/oranslice_rig/Papers_4-5/Paper_5/WPC/figures")
import axiom_style as S

S.setup()
SRC = "/home/kmanojp/oranslice_rig/experiments/results/gate3/curves.json"
OUT = "/home/kmanojp/oranslice_rig/Papers_4-5/Paper_5/WPC/figures/fig_learning"
PANELS = [("A3", "a", "A", "3 gNBs"), ("A19hex", "b", "A", "19 gNBs"), ("A37hex", "c", "A", "37 gNBs"),
          ("B3", "d", "B", "3 gNBs"), ("B7ring", "e", "B", "7 gNBs")]
ARMS = ["axiom2", "mappo_tuned", "single_agent_dqn", "independent_dqn"]


def band(m, reps=10000, chunk=500):
    """95% percentile bootstrap band of the per-episode mean over seeds (rows)."""
    rng = np.random.default_rng(0); n = m.shape[0]; out = []
    for _ in range(reps // chunk):
        idx = rng.integers(0, n, size=(chunk, n))
        out.append(m[idx].mean(axis=1))
    b = np.concatenate(out)
    return np.percentile(b, 2.5, axis=0), np.percentile(b, 97.5, axis=0)


def main():
    d = json.load(open(SRC))
    fig = S.figure("full", 86)
    W, H, x0, y0, gx, gy = 0.245, 0.335, 0.115, 0.115, 0.06, 0.135
    pos = [(x0 + i * (W + gx), y0 + H + gy) for i in range(3)] + [(x0 + i * (W + gx), y0) for i in range(2)]
    summ = {}
    for (key, letter, env, title), (px, py) in zip(PANELS, pos):
        ax = fig.add_axes([px, py, W, H]); summ[key] = {}
        for z, a in enumerate(reversed(ARMS)):
            runs = d[key]["arms"][a]["runs"]
            m = np.array([runs[s] for s in sorted(runs, key=int)], float)
            mu = m.mean(axis=0); lo, hi = band(m); x = np.arange(1, m.shape[1] + 1)
            col = S.POLICY[a]["color"]
            ax.fill_between(x, lo, hi, color=S.lighten(col, 0.72), lw=0, zorder=1 + z)
            ax.plot(x, mu, color=col, lw=0.9, zorder=10 + z)
            summ[key][a] = {"n_seeds": int(m.shape[0]), "episodes": int(m.shape[1]),
                            "first20_mean": float(mu[:20].mean()), "last20_mean": float(mu[-20:].mean()),
                            "last20_ci": [float(lo[-20:].mean()), float(hi[-20:].mean())]}
        ax.set_xlim(1, 300); ax.set_xticks([1, 100, 200, 300])
        ax.spines[["top", "right"]].set_visible(False)
        ax.text(0.0, 1.06, letter, transform=ax.transAxes, ha="left", va="bottom", fontweight="normal")
        t = S.ENV_TAG[env]
        ax.text(0.10, 1.06, f"Env {env}", transform=ax.transAxes, ha="left", va="bottom", color=t["tc"],
                bbox=dict(boxstyle="round,pad=0.2", fc=t["fc"], ec=t["ec"], lw=0.6))
        ax.text(1.0, 1.06, title, transform=ax.transAxes, ha="right", va="bottom")
        if letter in ("a", "d"):
            ax.set_ylabel("Training reward\nper gNB per step")
        if letter in ("d", "e", "c"):
            ax.set_xlabel("Training episode")
    lx, ly = pos[2][0] + 0.02, y0 + H - 0.03
    for i, a in enumerate(ARMS):
        col = S.POLICY[a]["color"]
        fig.lines.append(__import__("matplotlib").lines.Line2D([lx, lx + 0.05], [ly - i * 0.07, ly - i * 0.07], transform=fig.transFigure, color=col, lw=1.2))
        fig.text(lx + 0.065, ly - i * 0.07, S.POLICY[a]["label"], ha="left", va="center")
    fig.text(lx, ly - 4 * 0.07 + 0.02, "Bands, 95% CI\nover seeds", ha="left", va="top")
    facts = S.save(fig, OUT)
    json.dump({"panels": summ, "source": SRC}, open(OUT + "_summary.json", "w"), indent=1)
    print("[fig_learning]", facts, {k: {a: round(v["last20_mean"], 3) for a, v in s.items()} for k, s in summ.items()})


if __name__ == "__main__":
    main()
