"""Fig: every reported comparison of AXIOM with each learned baseline, beside its fresh-seed replication.

Rows are cluster sizes in Env A and Env B, one per baseline. For each, the paired per-seed difference AXIOM minus
baseline is shown as a mean with a 95% bootstrap CI, (a) in reward per gNB per step and (b) in priority-slice
compliance (cluster level), percentage points. Filled circles are the reported campaigns, hollow diamonds the
fresh-seed runs (M66 to M80), each pooled over the layouts it covers and paired within layout and seed. The figure
is descriptive: it shows estimates and 95% CIs only, and the paper's hypothesis tests keep their own pre-registered
families. Every plotted number is written to <out>_summary.json, which m66_verify checks.
"""
import json
import os
import sys

import numpy as np
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/scripts")
sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/plots")
from m62_analysis import boot_ci  # noqa: E402
from m66_verify import S15, S30, S30_19, prio, seeds_of  # noqa: E402
from paper5_common import MAIN_WIDTH_IN  # noqa: E402

RES = "/home/kmanojp/oranslice_rig/experiments/results"
BASE = [("single_agent_dqn", "DQN-SA", "#1baf7a"), ("independent_dqn", "DQN-I", "#eb6834"), ("mappo_tuned", "MAPPO", "#7a4fd0")]
LAY = ("fully_connected", "ring", "hex")
TAG = {"A": dict(fc="#e2e8f0", ec="#5a6b82", tc="#26344a"), "B": dict(fc="#f4ead6", ec="#9c7a45", tc="#4f3a15")}


def dir_seeds(cell):
    d = f"{RES}/{cell}/axiom2"
    return sorted(int(x[4:]) for x in os.listdir(d) if x.startswith("seed"))


def cells(env, n, sample):
    """(cell for AXIOM, cell for the baseline, seeds) triples that are paired within themselves."""
    if sample == "reported":
        if env == "A":
            if n == 3:
                return [("m65_reviewer/base", "m63_reviewer/base", S30)]
            if n in (7, 19):
                return [(f"m65_scaling/n{n}_{t}", f"m65_scaling/n{n}_{t}", S15 if n == 7 else S30_19) for t in LAY]
            return [("m73/A_n37_hex", "m73/A_n37_hex", S30_19)]
        if n == 3:
            return [("m64/n3_fully_connected", "m64/n3_fully_connected", S30)]
        if n == 7:
            return [(f"m64/n7_{t}", f"m64/n7_{t}", S15) for t in LAY]
        return [("m75/D_envB_n19_hex", "m75/D_envB_n19_hex", S15)]
    fresh = {("A", 3): ["m66_fresh/A_n3", "m66d_fresh/D1_A_n3"],
             ("A", 7): ["m66b_fresh/A_n7_ring", "m66b_fresh/A_n7_fully_connected", "m66c_fresh/C1_A_n7_hex", "m66c_fresh/C3_A_n7_fc"],
             ("A", 19): ["m66_fresh/A_n19_ring", "m66b_fresh/A_n19_hex", "m66c_fresh/C2_A_n19_fc"],
             ("A", 37): ["m74/A_n37_hex"],
             ("B", 3): ["m66_fresh/B_n3"],
             ("B", 7): ["m66_fresh/B_n7_ring", "m66c_fresh/C4_B_n7_fully_connected", "m66c_fresh/C4_B_n7_hex"],
             ("B", 19): ["m80/D_envB_n19_hex_fresh"]}[(env, n)]
    return [(c, c, dir_seeds(c)) for c in fresh]


def pairs(env, n, sample, base):
    out = []
    for c_ax, c_b, seeds in cells(env, n, sample):
        bc = c_b
        if sample == "reported" and env == "A" and n == 3 and base == "mappo_tuned":
            bc = "m65_reviewer/base"    # the reported three-gNB MAPPO comes from M65, the DQNs from M63
        a = seeds_of(c_ax, "axiom2", seeds)
        b = seeds_of(bc, base, seeds)
        for s in sorted(set(a) & set(b)):
            out.append(((a[s]["reward"] - b[s]["reward"]) / n, 100 * (prio(a[s]) - prio(b[s]))))
    return out


def main():
    out = "../../Papers_4-5/Paper_5/WPC/figures/fig_forest"
    rows = []
    for env, sizes in (("A", (3, 7, 19, 37)), ("B", (3, 7, 19))):
        for n in sizes:
            for sample in ("reported", "fresh"):
                for base, _, _ in BASE:
                    p = pairs(env, n, sample, base)
                    for m, k in (("reward", 0), ("sla", 1)):
                        d = np.array([x[k] for x in p])
                        rows.append({"env": env, "n": n, "sample": sample, "baseline": base, "metric": m, "n_pairs": len(d),
                                     "mean": float(d.mean()), "ci": list(boot_ci(d)), "wins": int((d > 0).sum()), "losses": int((d < 0).sum())})
    json.dump({"rows": rows}, open(out + "_summary.json", "w"), indent=1)

    fig = plt.figure(figsize=(MAIN_WIDTH_IN, 3.55))
    axR = fig.add_axes([0.2, 0.13, 0.36, 0.83])
    axS = fig.add_axes([0.62, 0.13, 0.36, 0.83])
    ypos, ylab, y = {}, [], 0.0
    blocks = []
    for env, sizes in (("A", (3, 7, 19, 37)), ("B", (3, 7, 19))):
        top = y
        for n in sizes:
            for k, (base, _, _) in enumerate(BASE):
                ypos[(env, n, base)] = y + k * 0.32
            ylab.append((y + 0.32, f"{n} gNBs"))
            y += 1.25
        blocks.append((env, top, y - 0.3))
        y += 0.45
    for ax, metric, xl in ((axR, "reward", "Reward per gNB per step,\nAXIOM minus baseline"), (axS, "sla", "Priority-slice SLA, points,\nAXIOM minus baseline")):
        for r in rows:
            if r["metric"] != metric:
                continue
            col = dict((b, c) for b, _, c in BASE)[r["baseline"]]
            yy = ypos[(r["env"], r["n"], r["baseline"])] + (0.12 if r["sample"] == "fresh" else -0.04)
            fresh = r["sample"] == "fresh"
            ax.plot(r["ci"], [yy, yy], color=col, lw=1.0, alpha=0.9, ls=(0, (2, 1)) if fresh else "-")
            ax.plot(r["mean"], yy, "D" if fresh else "o", ms=3.6 if fresh else 4.2, mec=col, mfc="white" if fresh else col, mew=1.0, zorder=3)
        ax.axvline(0, color="#555555", lw=0.8, ls="--")
        ax.set_ylim(y - 0.2, -0.45)
        ax.set_yticks([p for p, _ in ylab])
        ax.set_yticklabels([l for _, l in ylab] if ax is axR else [], fontsize=8.3)
        ax.tick_params(axis="y", length=0)
        ax.set_xlabel(xl, fontsize=8.3)
        ax.grid(True, axis="x", linewidth=0.4, alpha=0.4)
        ax.spines[["top", "right", "left"]].set_visible(False)
        for env, a, b in blocks:
            ax.axhspan(a - 0.35, b + 0.25, color=TAG[env]["fc"], alpha=0.35, lw=0, zorder=0)
    for env, a, b in blocks:
        yfig = 0.13 + 0.83 * (1 - ((a + b) / 2 - (-0.45)) / (y - 0.2 - (-0.45)))
        fig.text(0.015, yfig, f"Env {env}", fontsize=8.5, va="center", color=TAG[env]["tc"],
                 bbox=dict(boxstyle="round,pad=0.25", fc=TAG[env]["fc"], ec=TAG[env]["ec"], lw=0.6))
    for x_, t_ in ((0.005, "a"), (0.6, "b")):
        fig.text(x_ + (0.19 if t_ == "a" else 0.0), 0.995, t_, fontsize=9, va="top")
    handles = [Line2D([0], [0], color=c, lw=1.0, marker="o", mfc=c, mec=c, ms=4, label=l) for _, l, c in BASE]
    handles += [Line2D([0], [0], color="#444444", lw=1.0, marker="o", mfc="#444444", ms=4, label="reported"),
                Line2D([0], [0], color="#444444", lw=1.0, ls=(0, (2, 1)), marker="D", mfc="white", mec="#444444", ms=3.6, label="fresh seeds")]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.55, -0.1), ncol=5, fontsize=8.3, frameon=False,
               handlelength=1.2, columnspacing=0.9, handletextpad=0.35)
    fig.savefig(out + ".pdf", bbox_inches="tight", pad_inches=0.04)
    fig.savefig(out + ".png", dpi=200, bbox_inches="tight", pad_inches=0.04)
    for r in rows:
        print(r["env"], r["n"], r["sample"], r["baseline"], r["metric"], "pairs", r["n_pairs"], round(r["mean"], 3), [round(c, 3) for c in r["ci"]])


if __name__ == "__main__":
    main()
