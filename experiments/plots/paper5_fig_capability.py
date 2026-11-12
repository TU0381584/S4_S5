"""Fig. 10 (main paper, Discussion): what each controller offers. Option A of the redesign prototyped in
Papers_4-5/Paper_5/WPC/figures/fig10_variants/, drawn at the journal's 119 mm width.

a, four strips sharing the controller axis, Env A at 37 gNBs: priority-slice compliance, URLLC backlog delay
(control periods), parameters at execution, and compliance of the 7-gNB checkpoint run at 37 gNBs without retraining.
Mean with a 95% percentile bootstrap CI over seeds (scipy.stats.bootstrap, 10,000 resamples, default_rng(0)), and one
faint dot per seed.
b, four capabilities with a mark (met, partly met, not met) and a measured qualifier. No total score.

Sources, all per seed through m66_verify's independent reader:
  compliance at 37      m73/A_n37_{hex 30 seeds, ring 15, fully_connected 15} (AXIOM pooled as in Sec. 6.2), hex 30 for
                        the baselines and the static rule, M97 (m97/A_n37_hex) for the local rule tuned in Env A at 37
  URLLC delay           M77 recorder, m77/A_n37_hex and, for the tuned rule, m97/A_n37_hex_kpi
  parameters            m64/complexity.json, m73/complexity_n37.json
  transfer 7 to 37      M92, m92/A_{hex,ring,fully_connected}_n37/*_transfer
  past and steady load  Env B, 19 gNBs hex: reward per step minus the carried tuned rule's, M96 b for the learned
                        controllers, M76 for the static rule (same seeds, identical rule rows, checked)
  wins past the load    M96 b over 3, 7 and 19 gNBs at 110, 115 and 120% load, Holm per controller; the static rule
                        at 19 gNBs only (M76), the same test against the same rule
  steady load, Env A    reward at 37 gNBs hex, nominal load
  private training      AXIOM measured (centralised minus FedAvg reward, 30 seeds); the others from the training
                        design the paper states (Sec. 4 and Table 3): MAPPO's critic reads every gNB's features, DQN-SA
                        learns over the joint state, DQN-I trains each gNB on its own requests, rules learn no model.
Everything is saved to fig_capability_summary.json, which m66_verify recomputes.
"""
import glob
import json
import sys

import numpy as np
from scipy.stats import bootstrap, wilcoxon
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.path import Path  # noqa: E402

sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/scripts")
sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/plots")
from m66_verify import S15, S30_19, holm, paired, prio, seeds_of, tie_round  # noqa: E402
from paper5_fig_superiority import shift_row  # noqa: E402

ROOT = "/home/kmanojp/oranslice_rig/experiments/results"
FIG = "/home/kmanojp/oranslice_rig/Papers_4-5/Paper_5/WPC/figures"
OUT = f"{FIG}/fig_capability"
WIDTH_MM, HEIGHT_MM = 119.0, 100.0
FS = 8
AX, LEARN, RULE, INK, FAINT = "#0072B2", "#7F7F7F", "#D55E00", "#222222", "#BBBBBB"
ORDER = ["axiom2", "mappo_tuned", "single_agent_dqn", "independent_dqn", "rule_static", "rule_local"]
NAME = {"axiom2": "AXIOM", "mappo_tuned": "MAPPO", "single_agent_dqn": "DQN-SA", "independent_dqn": "DQN-I",
        "rule_static": "Static rule", "rule_local": "Tuned rule"}
LEARNED, RULES = tuple(ORDER[:4]), tuple(ORDER[4:])
COLOR = {a: (AX if a == "axiom2" else LEARN if a in LEARNED else RULE) for a in ORDER}
MARKER = {"axiom2": "o", "mappo_tuned": "s", "single_agent_dqn": "^", "independent_dqn": "v", "rule_static": "D", "rule_local": "P"}
LOADS = ("load_1.10", "load_1.15", "load_1.20")
SLA_OK, DELAY_OK = 90.0, 0.5

mpl.rcParams.update({"font.size": FS, "axes.labelsize": FS, "xtick.labelsize": FS, "ytick.labelsize": FS,
                     "pdf.fonttype": 42, "ps.fonttype": 42, "lines.linewidth": 0.6, "axes.linewidth": 0.6,
                     "xtick.major.width": 0.6, "xtick.minor.width": 0.5, "xtick.major.size": 2.5, "xtick.minor.size": 1.5,
                     "axes.facecolor": "none", "axes.edgecolor": INK, "text.color": INK, "axes.labelcolor": INK,
                     "xtick.color": INK, "ytick.color": INK, "axes.spines.top": False, "axes.spines.right": False,
                     "savefig.bbox": "standard", "savefig.pad_inches": 0.0, "axes.unicode_minus": True})


# ------------------------------------------------------------------ data
def ci(vals):
    v = np.asarray(list(vals), float)
    if len(v) < 2 or np.all(v == v[0]):
        return [float(v.mean())] * 2
    r = bootstrap((v,), np.mean, n_resamples=10000, confidence_level=0.95, method="percentile",
                  random_state=np.random.default_rng(0))
    return [float(r.confidence_interval.low), float(r.confidence_interval.high)]


def summ(per_seed):
    v = list(per_seed.values())
    return {"mean": float(np.mean(v)), "ci95": ci(v), "n": len(v), "per_seed": {str(k): float(x) for k, x in per_seed.items()}}


def delays(cell, arm):
    rows = {}
    for f in glob.glob(f"{ROOT}/{cell}/{arm}_*.json"):
        rows.update({int(k): v for k, v in json.load(open(f)).items()})
    return {s: rows[s]["kpi"]["urllc"]["delay_steps"] for s in sorted(rows) if rows[s]["kpi"]["urllc"]["delay_steps"] is not None}


def data():
    P = lambda r: 100 * prio(r)
    d = {}
    cx = json.load(open(f"{ROOT}/m64/complexity.json")); c37 = json.load(open(f"{ROOT}/m73/complexity_n37.json"))["37"]
    key = {"axiom2": "axiom2", "mappo_tuned": "mappo", "single_agent_dqn": "single_agent_dqn", "independent_dqn": "independent_dqn"}
    d["params"] = {a: {**{str(n): int(cx[str(n)][k]["params_execution"]) for n in (3, 7, 19)}, "37": int(c37[k]["params_execution"])}
                   for a, k in key.items()}
    ax = {}
    for t, ss in (("hex", S30_19), ("ring", S15), ("fully_connected", S15)):
        ax.update({f"{t}:{s}": P(r) for s, r in seeds_of(f"m73/A_n37_{t}", "axiom2", ss).items()})
    sla = {"axiom2": summ(ax)}
    for a in ("mappo_tuned", "single_agent_dqn", "independent_dqn", "rule_static"):
        sla[a] = summ({s: P(r) for s, r in seeds_of("m73/A_n37_hex", a, S30_19).items()})
    sla["rule_local"] = summ({s: P(r) for s, r in seeds_of("m97/A_n37_hex", "rule_local", S30_19).items()})
    d["sla37"] = sla
    dl = {a: summ(delays("m77/A_n37_hex", a)) for a in LEARNED + ("rule_static",)}
    dl["rule_local"] = summ(delays("m97/A_n37_hex_kpi", "rule_local_cell"))
    d["delay37"] = dl
    d["tuned_rule_A37"] = json.load(open(f"{ROOT}/m97/A_n37_hex/rule_local_selection.json"))["selected"]
    tr = {}
    for a in ("axiom2", "mappo_tuned"):
        tr[a] = summ({f"{t}:{s}": P(r) for t in ("hex", "ring", "fully_connected")
                      for s, r in seeds_of(f"m92/A_{t}_n37", f"{a}_transfer", S15).items()})
        tr[a]["by_layout"] = {t: float(np.mean([P(r) for r in seeds_of(f"m92/A_{t}_n37", f"{a}_transfer", S15).values()]))
                              for t in ("hex", "ring", "fully_connected")}
    d["transfer37"] = tr

    # Env B, 19 gNBs hex, reward per step relative to the carried tuned rule
    def b19(arm, L):
        if arm == "rule_static":
            return {s: shift_row("m76/b1_shift_n19", L, arm, s)["reward"] for s in S15}
        return {s: r["reward"] for s, r in seeds_of(f"m96/B_shift/n19_hex/{L}", arm, S15).items()}
    rule = {L: b19("rule_local_transfer", L) for L in ("nominal",) + LOADS}
    m76 = {L: {s: shift_row("m76/b1_shift_n19", L, "rule_local_transfer", s)["reward"] for s in S15} for L in rule}
    assert all(abs(m76[L][s] - rule[L][s]) < 1e-9 for L in rule for s in S15), "M76 and M96 tuned-rule rows differ"
    past, steady = {}, {}
    for a in LEARNED + ("rule_static",):
        rows = {L: b19(a, L) for L in ("nominal",) + LOADS}
        past[a] = summ({s: float(np.mean([rows[L][s] - rule[L][s] for L in LOADS])) for s in S15})
        past[a]["by_load"] = {L: float(np.mean([rows[L][s] - rule[L][s] for s in S15])) for L in LOADS}
        steady[a] = summ({s: rows["nominal"][s] - rule["nominal"][s] for s in S15})
    d["past19"], d["steady19"] = past, steady
    cells = {3: ("m96/B_shift/n3", list(range(905, 930)), "rule_local"), 7: ("m96/B_shift/n7_ring", S15, "rule_local"),
             19: ("m96/B_shift/n19_hex", S15, "rule_local_transfer")}
    wins = {}
    for a in LEARNED:
        t = {f"{n}|{L}": paired(seeds_of(f"{c}/{L}", a, ss), seeds_of(f"{c}/{L}", rl, ss)) for n, (c, ss, rl) in cells.items() for L in LOADS}
        h = holm({k: v["p"] for k, v in t.items()})
        wins[a] = {"wins": int(sum(v["diff"] > 0 and h[k] < 0.05 for k, v in t.items())), "tests": len(t)}
    # the static rule, at 19 gNBs only (M76): the same test against the same carried rule
    t = {L: paired({s: {"reward": shift_row("m76/b1_shift_n19", L, "rule_static", s)["reward"]} for s in S15},
                   {s: {"reward": rule[L][s]} for s in S15}) for L in LOADS}
    h = holm({k: v["p"] for k, v in t.items()})
    wins["rule_static"] = {"wins": int(sum(v["diff"] > 0 and h[k] < 0.05 for k, v in t.items())), "tests": len(t)}
    d["past_wins"] = wins
    rA = {a: summ({s: r["reward"] for s, r in seeds_of("m73/A_n37_hex", a, S30_19).items()}) for a in LEARNED + ("rule_static",)}
    rA["rule_local"] = summ({s: r["reward"] for s, r in seeds_of("m97/A_n37_hex", "rule_local", S30_19).items()})
    d["rewardA37"] = rA
    fd = {}
    for cen, fc, ss in (("m65_reviewer/base", "m65_m3", list(range(900, 910))), ("m65_reviewer/replication", "m65_m3_replication", list(range(1000, 1010)))):
        a_, b_ = seeds_of(cen, "axiom2", ss), seeds_of(fc, "fl_gat_ctde_sigma0.0", ss)
        fd.update({s: a_[s]["reward"] - b_[s]["reward"] for s in ss})
    a_ = seeds_of("m66_fresh/A_n3", "axiom2", list(range(3000, 3010))); b_ = {}
    for k in range(3000, 3010, 2):
        b_.update(seeds_of(f"m66b_fresh/m3_s{k}", "fl_gat_ctde_sigma0.0", [k, k + 1]))
    fd.update({s: a_[s]["reward"] - b_[s]["reward"] for s in range(3000, 3010)})
    d["fed_cost"] = summ(fd); d["fed_cost"]["p"] = float(wilcoxon(tie_round(list(fd.values()))).pvalue)
    best = max(("mappo_tuned", "single_agent_dqn", "independent_dqn"), key=lambda a: sla[a]["mean"])
    d["lead37"] = {"points": sla["axiom2"]["mean"] - sla[best]["mean"], "over": best}
    d["params_ratio_dqni"] = d["params"]["independent_dqn"]["37"] / d["params"]["axiom2"]["37"]
    return d


def sgn(x):
    return f"{x:+.1f}".replace("-", "−")


def table(d):
    """Rows of panel b: [label, {controller: [mark, qualifier]}]; marks yes, half, no, none."""
    tr = d["transfer37"]; rng = tr["axiom2"]["by_layout"].values()
    t = {"axiom2": ["yes" if min(rng) >= SLA_OK else "half", f"{min(rng):.0f}–{max(rng):.0f}%"],
         "mappo_tuned": ["yes" if tr["mappo_tuned"]["mean"] >= SLA_OK else "half", f"{tr['mappo_tuned']['mean']:.1f}%"],
         "single_agent_dqn": ["no", "fixed input"], "independent_dqn": ["no", "fixed input"],
         "rule_static": ["yes", "size-free"], "rule_local": ["yes", "7→19, Env B"]}
    W, past = d["past_wins"], d["past19"]
    p = {}
    for a in LEARNED + ("rule_static",):
        w = W[a]
        mark = "yes" if w["wins"] == w["tests"] else "half" if w["wins"] else "no"
        p[a] = [mark, sgn(past[a]["mean"]) + "/step" if mark == "yes" else f"{w['wins']} of {w['tests']} wins"]
    p["rule_local"] = ["none", "reference"]
    rA, st = d["rewardA37"], d["steady19"]
    topA = max(rA[a]["mean"] for a in rA)
    bestA = {a for a in rA if rA[a]["mean"] == topA}           # exact ties count as best
    bestB = {"rule_local"} if all(st[a]["mean"] < 0 for a in st) else {max(st, key=lambda a: st[a]["mean"])}
    s = {}
    for a in ORDER:
        if a in bestA and a in bestB:
            s[a] = ["yes", "best in A, B"]
        elif a in bestA:
            s[a] = ["yes", "best in A"]
        elif a in bestB:
            s[a] = ["yes", "best in B"]
        else:
            s[a] = ["no", sgn(st[a]["mean"]) + "/step"]
    f = d["fed_cost"]
    v = {"axiom2": ["yes" if f["p"] >= 0.05 else "half", "FedAvg"], "mappo_tuned": ["no", "pooled"],
         "single_agent_dqn": ["no", "pooled"], "independent_dqn": ["yes", "local"],
         "rule_static": ["yes", "no model"], "rule_local": ["yes", "no model"]}
    return [["Transfers without\nretraining", t], ["Beats tuned rule\npast its load", p], ["Best under\nsteady load", s],
            ["Private training", v]]


# ------------------------------------------------------------------ drawing
CHECK = Path([(-0.55, 0.0), (-0.15, -0.45), (0.6, 0.5)], [Path.MOVETO, Path.LINETO, Path.LINETO])
Y = {a: y for a, y in zip(ORDER, (0, 1, 2, 3, 4.5, 5.5))}


def mk(a, ms=4.0):
    return dict(marker=MARKER[a], ms=ms, mec=COLOR[a], mew=0.8, mfc=(COLOR[a] if a in LEARNED else "white"), ls="none")


def status(ax, x, y, kind, color, ms=5.6):
    if kind == "yes":
        ax.plot([x], [y], marker=CHECK, ms=ms, mec=color, mfc="none", mew=1.1, ls="none", clip_on=False)
    elif kind == "half":
        ax.plot([x], [y], marker="o", ms=ms * 0.85, mec=color, mfc=color, fillstyle="left", mfcalt="white", mew=0.8, ls="none", clip_on=False)
    elif kind == "no":
        ax.plot([x], [y], marker="x", ms=ms * 0.75, mec=color, mew=1.0, ls="none", clip_on=False)


def strip(fig, rect):
    ax = fig.add_axes(rect)
    ax.set_ylim(5.95, -1.55)
    ax.axhline(3.75, color=FAINT, lw=0.5)
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    return ax


def dots(ax, a, vals, rng):
    v = np.asarray(list(vals), float)
    ax.scatter(v, Y[a] + rng.uniform(-0.22, 0.22, len(v)), s=1.4, c=COLOR[a], alpha=0.35, lw=0, zorder=2)


def mean_ci(ax, a, s):
    ax.plot(s["ci95"], [Y[a]] * 2, color=COLOR[a], lw=1.0, solid_capstyle="butt", zorder=3)
    ax.plot([s["mean"]], [Y[a]], zorder=4, **mk(a))


def draw(d, rows):
    rng = np.random.default_rng(0)
    fig = plt.figure(figsize=(WIDTH_MM / 25.4, HEIGHT_MM / 25.4))
    fw, fh = (lambda mm: mm / WIDTH_MM), (lambda mm: mm / HEIGHT_MM)
    left, gap, top, h = 16.5, 5.0, 5.5, 40.0
    sw = (WIDTH_MM - left - 3 * gap - 3.0) / 4
    axs = [strip(fig, [fw(left + i * (sw + gap)), 1 - fh(top + h), fw(sw), fh(h)]) for i in range(4)]
    axs[0].set_yticks([Y[a] for a in ORDER]); axs[0].set_yticklabels([NAME[a] for a in ORDER])
    for t, a in zip(axs[0].get_yticklabels(), ORDER):
        t.set_color(AX if a == "axiom2" else INK)
    for ax in axs[1:]:
        ax.set_yticks([])
    dash = dict(color=INK, lw=0.6, ls=(0, (3, 2)), zorder=1)

    ax, sla = axs[0], d["sla37"]
    for a in ORDER:
        dots(ax, a, sla[a]["per_seed"].values(), rng); mean_ci(ax, a, sla[a])
    ax.axvline(SLA_OK, **dash); ax.set_xlim(0, 104); ax.set_xticks([0, 50, 100])
    ax.set_xlabel("Compliance,\n37 gNBs (%)")
    best, axm = sla[d["lead37"]["over"]]["mean"], sla["axiom2"]["mean"]
    yb = -0.95
    ax.plot([best, best, axm, axm], [yb + 0.18, yb, yb, yb + 0.18], color=AX, lw=0.6)
    ax.text(best - 3, yb + 0.02, f"+{d['lead37']['points']:.1f} pp vs\nbest learned", ha="right", va="center", color=AX, linespacing=0.95)
    ax.text(86, Y["rule_static"], "tuned to\nthis load", ha="right", va="center", color=RULE, linespacing=0.95)

    ax, dl = axs[1], d["delay37"]
    for a in ORDER:
        dots(ax, a, [v for v in dl[a]["per_seed"].values() if v > 0], rng); mean_ci(ax, a, dl[a])
    ax.set_xscale("log"); ax.set_xlim(5e-3, 100)
    ax.set_xticks([0.01, 1, 100]); ax.set_xticklabels(["0.01", "1", "100"]); ax.xaxis.set_minor_formatter(mpl.ticker.NullFormatter())
    ax.axvline(DELAY_OK, **dash)
    ax.set_xlabel("URLLC delay\n(control periods)")

    ax, P = axs[2], d["params"]
    for a in LEARNED:
        v = [P[a][n] for n in ("3", "7", "19", "37")]
        if len(set(v)) > 1:
            ax.plot([min(v), max(v)], [Y[a]] * 2, color=COLOR[a], lw=0.6, zorder=2)
            ax.plot([min(v)], [Y[a]], marker="|", ms=4, color=COLOR[a], mew=0.6)
        ax.plot([P[a]["37"]], [Y[a]], zorder=4, **mk(a))
    for a in RULES:
        ax.text(0.03, Y[a], "no params", transform=ax.get_yaxis_transform(), ha="left", va="center", color=RULE)
    ax.set_xscale("log"); ax.set_xlim(2e3, 2e6)
    ax.set_xticks([1e4, 1e5, 1e6]); ax.set_xticklabels(["10k", "100k", "1M"]); ax.xaxis.set_minor_formatter(mpl.ticker.NullFormatter())
    ax.set_xlabel("Parameters at\n37 gNBs (count)")
    ax.text(P["axiom2"]["37"] * 1.6, Y["axiom2"], f"{d['params_ratio_dqni']:.0f}× fewer\nthan DQN-I", ha="left", va="center",
            color=AX, linespacing=0.95)

    ax, tr = axs[3], d["transfer37"]
    for a in ("axiom2", "mappo_tuned"):
        dots(ax, a, tr[a]["per_seed"].values(), rng); mean_ci(ax, a, tr[a])
    for a in ("single_agent_dqn", "independent_dqn"):
        ax.text(2, Y[a], "× fixed input", ha="left", va="center", color=LEARN)
    dots(ax, "rule_static", sla["rule_static"]["per_seed"].values(), rng); mean_ci(ax, "rule_static", sla["rule_static"])
    ax.plot([50], [Y["rule_local"]], marker="o", ms=4.0, mec=FAINT, mfc="white", mew=0.8, ls="none", zorder=4)
    ax.text(50, Y["rule_local"] - 0.42, "n/t", ha="center", va="bottom", color="#666666")
    ax.axvline(SLA_OK, **dash); ax.set_xlim(0, 104); ax.set_xticks([0, 50, 100])
    ax.set_xlabel("After 7→37\ntransfer (%)")
    fig.text(fw(0.5), 1 - fh(2.5), "a", fontweight="bold", va="center")

    tb = fig.add_axes([0, 0, 1, fh(38)]); tb.set_xlim(0, WIDTH_MM); tb.set_ylim(38, 0); tb.axis("off")
    fig.text(fw(0.5), fh(37.2), "b", fontweight="bold", va="center")
    x0 = 24.0; cw = (WIDTH_MM - x0 - 0.5) / 6
    cx = {a: x0 + (i + 0.5) * cw for i, a in enumerate(ORDER)}
    tb.plot([3.5, WIDTH_MM - 0.5], [1.2, 1.2], color=INK, lw=0.8)
    tb.plot([3.5, WIDTH_MM - 0.5], [6.4, 6.4], color=INK, lw=0.5)
    for a in ORDER:
        tb.text(cx[a], 3.8, NAME[a], ha="center", va="center", color=AX if a == "axiom2" else INK)
    rh = 7.6
    tb.plot([x0 + 4 * cw] * 2, [1.2, 6.4 + 4 * rh + 0.4], color=FAINT, lw=0.5)
    for i, (lab, cells) in enumerate(rows):
        yc = 6.4 + (i + 0.5) * rh
        tb.text(3.5, yc, lab, ha="left", va="center", linespacing=0.95)
        for a in ORDER:
            kind, q = cells[a]
            status(tb, cx[a], yc - 1.7, kind, COLOR[a])
            tb.text(cx[a], yc + 1.9, q, ha="center", va="center", color="#444444")
    tb.plot([3.5, WIDTH_MM - 0.5], [6.4 + 4 * rh + 0.4] * 2, color=INK, lw=0.8)
    return fig


def check_layout(fig):
    """No two text labels may overlap, every label must lie inside the canvas, and no font is below 8 pt."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    W, H = fig.bbox.width, fig.bbox.height
    ts = [t for t in fig.findobj(mpl.text.Text) if t.get_visible() and t.get_text().strip()]
    assert min(t.get_fontsize() for t in ts) >= 8, "font below 8 pt"
    bb = [(t.get_text(), t.get_window_extent(r)) for t in ts]
    for s, b in bb:
        assert b.x0 >= -0.5 and b.y0 >= -0.5 and b.x1 <= W + 0.5 and b.y1 <= H + 0.5, f"text outside the canvas: {s!r}"
    pad = 0.4 / 25.4 * fig.dpi                  # at least 0.4 mm between any two labels
    grow = lambda b: mpl.transforms.Bbox([[b.x0 - pad / 2, b.y0 - pad / 2], [b.x1 + pad / 2, b.y1 + pad / 2]])
    bad = [(s1, s2) for i, (s1, b1) in enumerate(bb) for s2, b2 in bb[i + 1:] if grow(b1).overlaps(grow(b2))]
    assert not bad, f"overlapping text: {bad}"


def main():
    d = data()
    rows = table(d)
    fig = draw(d, rows)
    check_layout(fig)
    fig.savefig(OUT + ".pdf")
    fig.savefig(OUT + ".png", dpi=300)
    drop = ("sla37", "delay37", "transfer37", "past19", "steady19", "rewardA37")
    slim = {k: ({a: {x: y for x, y in v.items() if x != "per_seed"} for a, v in d[k].items()} if k in drop else d[k]) for k in d}
    slim["fed_cost"] = {x: y for x, y in d["fed_cost"].items() if x != "per_seed"}
    json.dump({"data": slim, "rows": rows, "thresholds": {"sla37": SLA_OK, "delay37": DELAY_OK}, "size_mm": [WIDTH_MM, HEIGHT_MM]},
              open(OUT + "_summary.json", "w"), indent=1)
    print(f"[fig_capability] {WIDTH_MM} x {HEIGHT_MM} mm; " + "; ".join(
        f"{l.splitlines()[0]}: " + ", ".join(f"{NAME[a]} {c[a][0]} {c[a][1]}" for a in ORDER) for l, c in rows))


if __name__ == "__main__":
    main()
