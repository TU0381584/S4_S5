"""Fig: AXIOM against the three learned baselines as the cluster grows.
(a) Env A at 3, 7, 19, and 37 gNBs, (b) Env B at 3, 7, and 19 gNBs, (c) Env A and (d) Env B capability radars.

Panels a and b are computed here from the stored evaluation logs (via m66_verify's
reader): x is reward per gNB per step, y is priority-slice compliance, each point a
policy at one cluster size with 95% bootstrap CIs on both axes. A policy keeps one
colour family, shaded light to dark from the smallest to the largest cluster. Every
plotted number is written to <out>_summary.json, which m66_verify checks. The radar
values are fractions of the best learned policy on each axis and are checked there too.
"""
import json
import sys

import numpy as np
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/scripts")
from m62_analysis import boot_ci  # noqa: E402
from m66_verify import S15, S30, S30_19, prio, seeds_of  # noqa: E402

mpl.rcParams.update({
    "font.size": 8.5, "axes.titlesize": 9, "axes.labelsize": 8.5,
    "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
    "axes.linewidth": 0.7, "pdf.fonttype": 42, "ps.fonttype": 42,
    "savefig.bbox": "tight",
})

C = {"AXIOM": "#2a78d6", "DQN-SA": "#1baf7a", "DQN-I": "#eb6834", "MAPPO": "#7a4fd0"}
M = {"AXIOM": "o", "DQN-SA": "s", "DQN-I": "^", "MAPPO": "D"}
ARM = {"AXIOM": "axiom2", "DQN-SA": "single_agent_dqn", "DQN-I": "independent_dqn", "MAPPO": "mappo_tuned"}
SIZES = {"A": (3, 7, 19, 37), "B": (3, 7, 19)}
LAYOUTS = ("fully_connected", "ring", "hex")


def rows_env_a(n, arm):
    """Env A cells as reported in the paper (three-gNB baselines reused from M63)."""
    if n == 3:
        cell = "m65_reviewer/base" if arm in ("axiom2", "mappo_tuned") else "m63_reviewer/base"
        return list(seeds_of(cell, arm, S30).values())
    if n in (7, 19):
        ss = S15 if n == 7 else S30_19
        return [r for t in LAYOUTS for r in seeds_of(f"m65_scaling/n{n}_{t}", arm, ss).values()]
    if arm == "axiom2":   # 37 gNBs, AXIOM pooled over hex 30, ring 15, fully-connected 15
        return [r for t, ss in (("hex", S30_19), ("ring", S15), ("fully_connected", S15))
                for r in seeds_of(f"m73/A_n37_{t}", arm, ss).values()]
    return list(seeds_of("m73/A_n37_hex", arm, S30_19).values())


def rows_env_b(n, arm):
    if n == 3:
        return list(seeds_of("m64/n3_fully_connected", arm, S30).values())
    if n == 7:
        return [r for t in LAYOUTS for r in seeds_of(f"m64/n7_{t}", arm, S15).values()]
    return list(seeds_of("m75/D_envB_n19_hex", arm, S15).values())


def shade(colour, f):
    c = np.array(to_rgb(colour))
    return tuple(1 - f * (1 - c))


def compute():
    out = {}
    for env, fn in (("A", rows_env_a), ("B", rows_env_b)):
        for name, arm in ARM.items():
            for n in SIZES[env]:
                rows = fn(n, arm)
                x = [r["reward"] / n for r in rows]
                y = [100 * prio(r) for r in rows]
                out.setdefault(env, {}).setdefault(name, {})[str(n)] = {
                    "n_runs": len(rows), "x": float(np.mean(x)), "x_ci": list(boot_ci(x)),
                    "y": float(np.mean(y)), "y_ci": list(boot_ci(y)),
                    "no_collapse": 1.0 - sum(r["collapsed"] for r in rows) / len(rows)}
    return out


def draw_env(ax, data, env, xlab):
    sizes = SIZES[env]
    fr = np.linspace(0.38, 1.0, len(sizes))
    for name in ("MAPPO", "DQN-I", "DQN-SA", "AXIOM"):
        pts = [data[env][name][str(n)] for n in sizes]
        ax.plot([p["x"] for p in pts], [p["y"] for p in pts], color=C[name], lw=0.8, alpha=0.55, zorder=2)
        for f, n, p in zip(fr, sizes, pts):
            ax.errorbar(p["x"], p["y"], xerr=[[p["x"] - p["x_ci"][0]], [p["x_ci"][1] - p["x"]]],
                        yerr=[[p["y"] - p["y_ci"][0]], [p["y_ci"][1] - p["y"]]], fmt=M[name], ms=5 if name == "AXIOM" else 4.2,
                        mfc=shade(C[name], f), mec=C[name], mew=0.7, ecolor=shade(C[name], max(f, 0.55)), elinewidth=0.7,
                        capsize=1.5, zorder=4 if name == "AXIOM" else 3)
            if name == "AXIOM":
                off = (7, -11) if (env == "A" and n == 37) else (0, 6) if env == "A" else (6, 4)
                ax.annotate(str(n), (p["x"], p["y"]), textcoords="offset points", xytext=off, ha="center" if env == "A" else "left",
                            fontsize=8, color=C[name])
    ax.set_xlabel(f"Env {env} reward per gNB per step")
    ax.set_ylabel(f"Env {env} priority-slice SLA, %")
    ax.grid(True, linewidth=0.4, alpha=0.4)
    ax.spines[["top", "right"]].set_visible(False)


RADAR = {   # (axis code, full name, cluster size, kind) with kind r reward per step, y priority SLA, c no-collapse share
    "A": [("R3", "Reward 3 gNBs", "3", "r"), ("R37", "Reward 37 gNBs", "37", "r"), ("S7", "Priority SLA 7 gNBs", "7", "y"),
          ("S19", "Priority SLA 19 gNBs", "19", "y"), ("S37", "Priority SLA 37 gNBs", "37", "y"), ("NC37", "No collapse 37 gNBs", "37", "c")],
    "B": [("R3", "Reward 3 gNBs", "3", "r"), ("R7", "Reward 7 gNBs", "7", "r"), ("R19", "Reward 19 gNBs", "19", "r"),
          ("S3", "Priority SLA 3 gNBs", "3", "y"), ("S7", "Priority SLA 7 gNBs", "7", "y"), ("S19", "Priority SLA 19 gNBs", "19", "y")],
}


def radar_values(data, env):
    """Each axis as a fraction of the best learned policy on it (reward per step, compliance, or no-collapse share)."""
    raw = {}
    for name in ARM:
        raw[name] = []
        for _, _, n, kind in RADAR[env]:
            p = data[env][name][n]
            raw[name].append(p["x"] * int(n) if kind == "r" else p["y"] if kind == "y" else p["no_collapse"])
    best = [max(raw[k][i] for k in raw) for i in range(len(RADAR[env]))]
    return {k: [v / b for v, b in zip(raw[k], best)] for k in raw}


def draw_radar(ax, data, env):
    labels = [c for c, _, _, _ in RADAR[env]]
    vals = radar_values(data, env)
    data.setdefault("radar", {})[env] = {"axes": [f"Env {env} {d}" for _, d, _, _ in RADAR[env]], "codes": labels, "fractions": vals}
    ax.set_title(f"Env {env}, fraction of best learned policy", fontsize=8.5, pad=24)
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
    ax.tick_params(axis="x", pad=2)
    for lab_, a_ in zip(ax.get_xticklabels(), ang[:-1]):
        s_ = np.sin(a_)
        lab_.set_horizontalalignment("left" if s_ > 0.1 else "right" if s_ < -0.1 else "center")
    ax.grid(linewidth=0.4, alpha=0.5)
    zbase = {"AXIOM": 4, "DQN-I": 5, "DQN-SA": 6, "MAPPO": 5}
    LS = {"AXIOM": (0, (1, 1.35)), "DQN-I": (0, (5, 2)), "DQN-SA": "-", "MAPPO": (0, (3, 1, 1, 1))}
    for name in ["AXIOM", "DQN-I", "DQN-SA", "MAPPO"]:
        v = vals[name] + vals[name][:1]
        ax.plot(ang, v, color=C[name], linewidth=1.9 if name == "AXIOM" else 1.5, linestyle=LS[name], marker=M[name],
                markersize=4.5 if name == "AXIOM" else 5, zorder=zbase[name])
        ax.fill(ang, v, color=C[name], alpha=0.16 if name == "AXIOM" else 0.05, zorder=2)
    return LS


def main():
    out = "../../Papers_4-5/Paper_5/WPC/figures/fig10_axiom_superiority"
    data = compute()
    fig = plt.figure(figsize=(5.16, 5.65))
    # one row per environment, scatter then radar (a, b Env A; c, d Env B)
    axA = fig.add_axes([0.105, 0.635, 0.37, 0.315])
    axRA = fig.add_axes([0.6, 0.625, 0.33, 0.33], projection="polar")
    axB = fig.add_axes([0.105, 0.2, 0.37, 0.315])
    axRB = fig.add_axes([0.6, 0.15, 0.33, 0.33], projection="polar")
    draw_env(axA, data, "A", None)
    draw_env(axB, data, "B", None)
    axA.set_ylim(25, 102)
    axB.set_ylim(10, 72)
    draw_radar(axRA, data, "A")
    LS = draw_radar(axRB, data, "B")
    for x_, y_, t_ in ((0.01, 0.995, "a"), (0.52, 0.995, "b"), (0.01, 0.56, "c"), (0.52, 0.56, "d")):
        fig.text(x_, y_, t_, fontsize=9, va="top")
    handles = [Line2D([0], [0], color=C[n], marker=M[n], linewidth=1.5, linestyle=LS[n], label=n)
               for n in ["AXIOM", "DQN-SA", "DQN-I", "MAPPO"]]
    fig.text(0.5, 0.068, "R reward per step, S priority-slice SLA, NC no collapse, each followed by the number of gNBs",
             ha="center", va="center", fontsize=8)
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.005), ncol=4, frameon=False,
               fontsize=8.5, handlelength=1.8, columnspacing=1.2)
    shades = [Patch(facecolor=shade("#6b6b6b", f), edgecolor="#6b6b6b", label=l)
              for f, l in zip(np.linspace(0.38, 1.0, 4), ("3 gNBs", "7 gNBs", "19 gNBs", "37 gNBs"))]
    fig.legend(handles=shades, loc="lower center", bbox_to_anchor=(0.5, -0.04), ncol=4, frameon=False,
               fontsize=8.5, handlelength=1.2, columnspacing=1.2)
    fig.savefig(out + ".pdf", bbox_inches="tight", pad_inches=0.02)
    fig.savefig(out + ".png", dpi=200, bbox_inches="tight", pad_inches=0.02)
    json.dump(data, open(out + "_summary.json", "w"), indent=1)
    print("wrote", out)
    for env in ("A", "B"):
        for name in ARM:
            print(env, name, {n: (round(v["x"], 2), round(v["y"], 1), v["n_runs"]) for n, v in data[env][name].items()})
        print("radar", env, {k: [round(x, 3) for x in v] for k, v in data["radar"][env]["fractions"].items()})


if __name__ == "__main__":
    main()
