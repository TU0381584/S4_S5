#!/usr/bin/env python3
"""Fig. 10, option A: dot-plot strips (a) and a capability table (b). Every value comes from data.json (data.py).

a, four strips sharing the controller axis: compliance at 37 gNBs, URLLC backlog delay, parameters, and compliance
after moving from 7 to 37 gNBs without retraining. Mean with 95% bootstrap CI, faint dots per seed.
b, a booktabs-style table of four capabilities with a mark and a short qualifier per cell. No total score.
Run: python fig10_A.py
"""
import os
import sys

import numpy as np
import matplotlib as mpl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style as S  # noqa: E402
from data import load  # noqa: E402

S.setup()
import matplotlib.pyplot as plt  # noqa: E402

D = load()
Y = {a: y for a, y in zip(S.ORDER, (0, 1, 2, 3, 4.5, 5.5))}
DIV = 3.75
JIT = np.random.default_rng(0)


def row_dots(ax, a, vals, log=False):
    v = np.asarray(list(vals), float)
    if log:
        v = v[v > 0]
    y = Y[a] + JIT.uniform(-0.22, 0.22, len(v))
    ax.scatter(v, y, s=1.6, c=S.COLOR[a], alpha=0.35, lw=0, zorder=2)


def row_mean(ax, a, m, lo, hi):
    ax.plot([lo, hi], [Y[a], Y[a]], color=S.COLOR[a], lw=1.0, solid_capstyle="butt", zorder=3)
    ax.plot([m], [Y[a]], zorder=4, **S.marker_kw(a, ms=4.2))


def nt(ax, a, x, text="n/t"):
    ax.plot([x], [Y[a]], marker="o", ms=4.2, mec=S.FAINT, mfc="white", mew=0.8, ls="none", zorder=4)
    ax.text(x, Y[a] - 0.42, text, ha="center", va="bottom", color="#666666")


def strip_axes(fig, rect):
    ax = fig.add_axes(rect)
    ax.set_ylim(5.95, -1.25)
    ax.axhline(DIV, color=S.FAINT, lw=0.5)
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    return ax


def main():
    W = S.WIDTH_IN
    H = 104 / 25.4
    fig = plt.figure(figsize=(W, H))
    fh = lambda mm: mm / 104          # figure fraction from mm, vertical
    fw = lambda mm: mm / S.WIDTH_MM   # horizontal
    left, gap, top_a, h_a = 17.5, 6.5, 98.0, 42.0
    sw = (S.WIDTH_MM - left - 3 * gap - 1.5) / 4
    axs = [strip_axes(fig, [fw(left + i * (sw + gap)), fh(104 - top_a + 0), fw(sw), fh(h_a)]) for i in range(4)]
    for ax in axs:
        ax.set_position([ax.get_position().x0, 1 - fh(6 + h_a), ax.get_position().width, fh(h_a)])
    axs[0].set_yticks([Y[a] for a in S.ORDER])
    axs[0].set_yticklabels([S.NAME[a] for a in S.ORDER])
    for t, a in zip(axs[0].get_yticklabels(), S.ORDER):
        t.set_color(S.AX if a == "axiom2" else S.INK)
    for ax in axs[1:]:
        ax.set_yticks([])

    # 1. compliance at 37 gNBs
    ax = axs[0]
    sla = D["sla37"]
    for a in S.ORDER:
        if a in sla:
            row_dots(ax, a, sla[a]["per_seed"].values())
            row_mean(ax, a, sla[a]["mean"], *sla[a]["ci95"])
        else:
            nt(ax, a, 50)
    ax.axvline(90, color=S.INK, lw=0.6, ls=(0, (3, 2)), zorder=1)
    ax.set_xlim(0, 104); ax.set_xticks([0, 50, 100])
    ax.set_xlabel("Compliance,\n37 gNBs (%)")
    lead = D["lead37"]["points"]; best = D["sla37"][D["lead37"]["over"]]["mean"]; axm = sla["axiom2"]["mean"]
    yb = -0.62
    ax.plot([best, best, axm, axm], [yb + 0.18, yb, yb, yb + 0.18], color=S.AX, lw=0.6)
    ax.text(best - 3, yb + 0.05, f"+{lead:.1f} pp vs\nbest learned", ha="right", va="center", color=S.AX, linespacing=0.95)
    st = sla["rule_static"]["mean"]
    ax.text(86, Y["rule_static"], "tuned to\nthis load", ha="right", va="center", color=S.RULE, linespacing=0.95)

    # 2. URLLC delay, log scale
    ax = axs[1]
    dl = D["delay37"]
    for a in S.ORDER:
        if a in dl:
            row_dots(ax, a, dl[a]["per_seed"].values(), log=True)
            row_mean(ax, a, dl[a]["mean"], *dl[a]["ci95"])
        else:
            nt(ax, a, 0.3)
    ax.set_xscale("log")
    allv = [v for a in dl for v in dl[a]["per_seed"].values() if v > 0]
    ax.set_xlim(10 ** np.floor(np.log10(min(allv))), 10 ** np.ceil(np.log10(max(allv))))
    ax.xaxis.set_major_locator(mpl.ticker.LogLocator(numticks=4))
    ax.xaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.xaxis.set_minor_formatter(mpl.ticker.NullFormatter())
    ax.axvline(0.5, color=S.INK, lw=0.6, ls=(0, (3, 2)), zorder=1)
    ax.set_xlabel("URLLC delay\n(control periods)")

    # 3. parameters at execution, log scale; a line from 3 to 37 gNBs where the count grows
    ax = axs[2]
    P = D["params"]
    for a in S.LEARNED:
        v = [P[a][n] for n in ("3", "7", "19", "37")]
        if len(set(v)) > 1:
            ax.plot([min(v), max(v)], [Y[a], Y[a]], color=S.COLOR[a], lw=0.6, zorder=2)
            ax.plot([min(v)], [Y[a]], marker="|", ms=4, color=S.COLOR[a], mew=0.6)
        ax.plot([P[a]["37"]], [Y[a]], zorder=4, **S.marker_kw(a, ms=4.2))
    for a in S.RULES:
        ax.text(0.02, Y[a], "no learned params", transform=ax.get_yaxis_transform(), ha="left", va="center", color=S.RULE)
    ax.set_xscale("log"); ax.set_xlim(2e3, 2e6)
    ax.set_xticks([1e4, 1e5, 1e6]); ax.set_xticklabels(["10k", "100k", "1M"])
    ax.xaxis.set_minor_formatter(mpl.ticker.NullFormatter())
    ax.set_xlabel("Parameters, 37 gNBs\n(count; line: 3 gNBs)")
    ax.text(P["axiom2"]["37"] * 1.6, Y["axiom2"] - 0.05, f"{D['params_ratio_dqni']:.0f}× fewer\nthan DQN-I", ha="left", va="center",
            color=S.AX, linespacing=0.95)

    # 4. compliance after the 7-gNB checkpoint is run at 37 gNBs
    ax = axs[3]
    tr = D["transfer37"]
    for a in ("axiom2", "mappo_tuned"):
        row_dots(ax, a, tr[a]["per_seed"].values())
        row_mean(ax, a, tr[a]["mean"], *tr[a]["ci95"])
    for a in ("single_agent_dqn", "independent_dqn"):
        ax.text(2, Y[a], "× fixed input", ha="left", va="center", color=S.LEARN)
    row_dots(ax, "rule_static", sla["rule_static"]["per_seed"].values())
    row_mean(ax, "rule_static", sla["rule_static"]["mean"], *sla["rule_static"]["ci95"])
    nt(ax, "rule_local", 50)
    ax.axvline(90, color=S.INK, lw=0.6, ls=(0, (3, 2)), zorder=1)
    ax.set_xlim(0, 104); ax.set_xticks([0, 50, 100])
    ax.set_xlabel("Compliance at 37,\ntrained at 7 (%)")
    fig.text(fw(1.0), 1 - fh(3.5), "a", fontweight="bold", va="center")

    # b. capability table
    tb = fig.add_axes([0, 0, 1, fh(38)])
    tb.set_xlim(0, S.WIDTH_MM); tb.set_ylim(38, 0); tb.axis("off")
    fig.text(fw(1.0), fh(37), "b", fontweight="bold", va="center")
    x0, cw = 29.0, (S.WIDTH_MM - 29.0 - 1.0) / 6
    cx = {a: x0 + (i + 0.5) * cw for i, a in enumerate(S.ORDER)}
    tb.plot([4, S.WIDTH_MM - 1], [1.2, 1.2], color=S.INK, lw=0.8)
    tb.plot([4, S.WIDTH_MM - 1], [6.4, 6.4], color=S.INK, lw=0.5)
    for a in S.ORDER:
        tb.text(cx[a], 3.8, S.NAME[a], ha="center", va="center", color=S.AX if a == "axiom2" else S.INK)
    tb.plot([x0 + 4 * cw, x0 + 4 * cw], [1.2, 37.2], color=S.FAINT, lw=0.5)
    rows = table_rows()
    rh = 7.6
    for i, (lab, cells) in enumerate(rows):
        yc = 6.4 + (i + 0.5) * rh
        tb.text(4, yc, lab, ha="left", va="center", linespacing=0.95)
        for a in S.ORDER:
            kind, q = cells[a]
            col = S.COLOR[a] if kind != "nt" else S.FAINT
            S.status(tb, cx[a] - 0.5 * max(len(q), 1) * 0.0 - 0.0, yc - 1.7, kind, col, ms=6.0)
            tb.text(cx[a], yc + 1.9, q, ha="center", va="center", color="#444444")
    tb.plot([4, S.WIDTH_MM - 1], [6.4 + 4 * rh + 0.4, 6.4 + 4 * rh + 0.4], color=S.INK, lw=0.8)
    return S.save(fig, "fig10_A")


def sgn(x):
    return f"{x:+.1f}".replace("-", "\u2212")


def table_rows():
    """Marks: yes, half, no, nt. Every qualifier is computed from data.json; the rules' private-training entries and the
    learned baselines' follow from the training design (data.json notes.private_training)."""
    tr, sla, P = D["transfer37"], D["sla37"], D["params"]
    rng = tr["axiom2"]["by_layout"]
    t = {"axiom2": ("yes" if min(rng.values()) >= 90 else "half", f"{min(rng.values()):.0f}–{max(rng.values()):.0f}%"),
         "mappo_tuned": ("yes" if tr["mappo_tuned"]["mean"] >= 90 else "half", f"{tr['mappo_tuned']['mean']:.1f}%"),
         "single_agent_dqn": ("no", "fixed input"), "independent_dqn": ("no", "fixed input"),
         "rule_static": ("yes", "size-free"), "rule_local": ("yes", "7→19, Env B")}
    W = D["past_wins_m96"]
    ov = D["over_tuned_rule_m76"]
    p = {"axiom2": ("yes" if W["axiom2"]["wins"] == W["axiom2"]["tests"] else "half", sgn(D["past19"]["axiom2"]["mean"]) + "/step")}
    for a in ("mappo_tuned", "single_agent_dqn", "independent_dqn"):
        w = W[a]
        p[a] = ("yes" if w["wins"] == w["tests"] else "half" if w["wins"] else "no", f"{w['wins']} of {w['tests']} wins")
    ps = D["past19"]["rule_static"]["mean"]
    p["rule_static"] = ("yes" if ps > 0 else "no", sgn(ps) + "/step")
    p["rule_local"] = ("none", "reference")
    rA = D["rewardA37"]; st19 = D["steady19"]
    topA = max(rA, key=lambda a: rA[a]["mean"])
    topB = "rule_local" if all(st19[a]["mean"] < 0 for a in st19) else max(st19, key=lambda a: st19[a]["mean"])
    s = {}
    tops = {a for a in rA if rA[a]["mean"] == rA[topA]["mean"]}     # exact ties count as best
    for a in S.ORDER:
        if a in tops and a == topB:
            s[a] = ("yes", "best, A and B")
        elif a in tops:
            s[a] = ("yes", "best, Env A")
        elif a == topB:
            s[a] = ("yes", "best, Env B")
        else:
            s[a] = ("no", sgn(st19[a]["mean"]) + "/step") if a in st19 else ("no", "")
    f = D["fed_cost"]
    v = {"axiom2": ("yes" if f["p_wilcoxon"] >= 0.05 else "half", "FedAvg"),
         "mappo_tuned": ("no", "pooled data"), "single_agent_dqn": ("no", "pooled data"), "independent_dqn": ("yes", "local only"),
         "rule_static": ("yes", "no model"), "rule_local": ("yes", "no model")}
    return [("Transfers without\nretraining", t), ("Beats tuned rule\npast its load", p), ("Best under\nsteady load", s), ("Private training", v)]


if __name__ == "__main__":
    main()
