"""Fig: AXIOM against the three learned baselines as the cluster grows.
(a, c) Env A and Env B reward per gNB against compliance, (b, d) capability radars, (e) Env A compliance under rising load, (f) Env B reward over the tuned rule as load shifts.

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
import matplotlib.ticker  # noqa: F401  (mpl.ticker for panel f)
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


RES = "/home/kmanojp/oranslice_rig/experiments/results"


def log_row(path):
    """One evaluation log read with m66_verify's reader, plain or gzipped."""
    import os
    from m66_verify import read
    for p in (path, path + ".gz"):
        if os.path.exists(p):
            return read(p)
    raise FileNotFoundError(path)


def shift_row(cell, shift, arm, seed):
    base = f"{RES}/{cell}/{shift}/{arm}/seed{seed}/"
    return log_row(base + ("omega_log.jsonl" if arm == "axiom2" else "lb_only/offline_eval/rep_0/omega_log.jsonl"))


LOAD_A = (("1.05", None), ("1.10", "m76/e_load1.10_n19_hex"), ("1.20", "m76/e_load1.20_n19_hex"))
LOAD_B = {3: ("m72/B_shift/n3", "rule_local", list(range(905, 930)), ("load_0.80", "nominal", "load_1.05", "load_1.10", "load_1.15", "load_1.20")),
          7: ("m72/B_shift/n7_ring", "rule_local", S15, ("nominal", "load_1.10", "load_1.20")),
          19: ("m76/b1_shift_n19", "rule_local_transfer", S15, ("nominal", "load_1.10", "load_1.15", "load_1.20"))}


def load_data():
    """e: Env A priority-slice compliance at nineteen gNBs (hex, 15 seeds) as offered load rises from the nominal 105% of
    the slice shares; f: Env B reward per gNB of AXIOM over the tuned rule, paired per seed, as load departs from the
    rule's tuning conditions, with neither retrained nor re-tuned."""
    out = {"A": {}, "B": {}}
    for name, arm in list(ARM.items()) + [("Static rule", "rule_static")]:
        for load, cell in LOAD_A:
            if cell is None:
                rows = list(seeds_of("m70/R1/A_n19_hex" if arm == "rule_static" else "m65_scaling/n19_hex", arm, S15).values())
            else:
                rows = list(seeds_of(cell, arm, S15).values())
            y = [100 * prio(r) for r in rows]
            out["A"].setdefault(name, {})[load] = {"n_runs": len(rows), "y": float(np.mean(y)), "y_ci": list(boot_ci(y))}
    for n, (cell, rule, seeds, shifts) in LOAD_B.items():
        for sh in shifts:
            d = [(shift_row(cell, sh, "axiom2", s)["reward"] - shift_row(cell, sh, rule, s)["reward"]) / n for s in seeds]
            load = "1.00" if sh == "nominal" else sh.split("_")[1]
            out["B"].setdefault(str(n), {})[load] = {"n_runs": len(d), "d": float(np.mean(d)), "d_ci": list(boot_ci(d))}
    return out


def draw_load_a(ax, data):
    xs = [float(l) * 100 for l, _ in LOAD_A]
    for name in ("MAPPO", "DQN-I", "DQN-SA", "AXIOM"):
        pts = [data["load"]["A"][name][l] for l, _ in LOAD_A]
        ax.errorbar(xs, [p["y"] for p in pts], yerr=[[p["y"] - p["y_ci"][0] for p in pts], [p["y_ci"][1] - p["y"] for p in pts]],
                    fmt="-" + M[name], color=C[name], ms=4.5 if name == "AXIOM" else 4, lw=1.6 if name == "AXIOM" else 1.0,
                    elinewidth=0.7, capsize=1.5, zorder=4 if name == "AXIOM" else 3)
    st = [data["load"]["A"]["Static rule"][l]["y"] for l, _ in LOAD_A]
    ax.plot(xs, st, color="#555555", lw=1.0, ls="--", zorder=2)
    ax.annotate("static rule", (xs[1], st[1]), textcoords="offset points", xytext=(4, 6), fontsize=8, color="#555555")
    ax.set_xticks(xs)
    ax.set_xlabel("Offered load at 19 gNBs, %")
    ax.set_ylabel("Env A priority SLA, %")
    ax.grid(True, axis="y", linewidth=0.4, alpha=0.4)
    ax.spines[["top", "right"]].set_visible(False)


def draw_load_b(ax, data):
    sizes = (3, 7, 19)
    sty = {3: (":", "o"), 7: ("--", "s"), 19: ("-", "^")}
    for f, n in zip(np.linspace(0.45, 1.0, 3), sizes):
        pts = sorted(data["load"]["B"][str(n)].items(), key=lambda kv: float(kv[0]))
        xs = [100 * float(k) for k, _ in pts]
        ys = [v["d"] for _, v in pts]
        ax.errorbar(xs, ys, yerr=[[v["d"] - v["d_ci"][0] for _, v in pts], [v["d_ci"][1] - v["d"] for _, v in pts]],
                    fmt=sty[n][1], ls=sty[n][0], color=shade(C["AXIOM"], f), mec=C["AXIOM"], ms=4, lw=1.4, elinewidth=0.7, capsize=1.5, zorder=3,
                    label=str(n))
    ax.axhline(0, color="#555555", lw=0.8, ls="--", zorder=1)
    ax.set_xticks([80, 100, 120])
    ax.yaxis.set_major_formatter(mpl.ticker.FormatStrFormatter("%.1f"))
    ax.legend(loc="upper left", title="gNBs", title_fontsize=8, fontsize=8, frameon=False, handlelength=1.0, borderpad=0.1, labelspacing=0.15, handletextpad=0.3)
    ax.set_xlabel("Offered load, %")
    ax.set_ylabel("Env B AXIOM lead per gNB")
    ax.grid(True, axis="y", linewidth=0.4, alpha=0.4)
    ax.spines[["top", "right"]].set_visible(False)


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
    data["load"] = load_data()
    fig = plt.figure(figsize=(5.16, 4.85))
    # one row per environment: scatter, radar, reward against the rule (a, b, e Env A; c, d, f Env B)
    axA = fig.add_axes([0.085, 0.665, 0.23, 0.305])
    axRA = fig.add_axes([0.375, 0.655, 0.215, 0.25], projection="polar")
    axE = fig.add_axes([0.745, 0.665, 0.245, 0.305])
    axB = fig.add_axes([0.085, 0.215, 0.23, 0.305])
    axRB = fig.add_axes([0.375, 0.22, 0.215, 0.25], projection="polar")
    axF = fig.add_axes([0.745, 0.215, 0.245, 0.305])
    draw_env(axA, data, "A", None)
    draw_env(axB, data, "B", None)
    axA.set_ylim(25, 102)
    axB.set_ylim(10, 72)
    draw_radar(axRA, data, "A")
    LS = draw_radar(axRB, data, "B")
    draw_load_a(axE, data)
    draw_load_b(axF, data)
    for x_, y_, t_ in ((0.005, 0.995, "a"), (0.345, 0.995, "b"), (0.655, 0.995, "e"), (0.005, 0.555, "c"), (0.345, 0.555, "d"), (0.655, 0.555, "f")):
        fig.text(x_, y_, t_, fontsize=9, va="top")
    for y_, env_ in ((0.995, "A"), (0.555, "B")):
        fig.text(0.37, y_, f"Env {env_}, share of best", fontsize=8, va="top", ha="left")
    handles = [Line2D([0], [0], color=C[n], marker=M[n], linewidth=1.5, linestyle=LS[n], label=n)
               for n in ["AXIOM", "DQN-SA", "DQN-I", "MAPPO"]]
    fig.text(0.5, 0.075, "R reward per step, S priority-slice SLA, NC no collapse, each followed by the number of gNBs",
             ha="center", va="center", fontsize=8)
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, -0.025), ncol=4, frameon=False,
               fontsize=8.5, handlelength=1.8, columnspacing=1.2)
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
