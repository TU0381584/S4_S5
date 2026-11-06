"""Fig: what each controller offers (top) and AXIOM's main margins (bottom), main paper, Discussion.

Top, a matrix of eight criteria. A criterion is met (filled), partly met (half), not met (open), or not tested (dash)
by the fixed rules in matrix(). Bottom, six margins of AXIOM. Every value is computed here from stored results:
execution parameters from the complexity records (m64 at 3, 7 and 19 gNBs, m73 at 37), transfer from seven gNBs
from M92, Env A compliance and URLLC backlog delay at 37 gNBs from the scaling cells and the M77 recorder, behaviour
past and at the rules' tuning load from the regime map's summary, Env B reward against MAPPO from the reported cells,
and the margin over the carried tuned rule from the M76 load-shift runs. Everything is saved to <out>_summary.json,
which m66_verify recomputes.
"""
import glob
import json
import sys

import numpy as np
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, FancyBboxPatch, Wedge  # noqa: E402

sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/scripts")
sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/plots")
from m66_verify import S15, S30, S30_19, prio, seeds_of, paired  # noqa: E402
from paper5_fig_superiority import shift_row  # noqa: E402

mpl.rcParams.update({"font.size": 8, "pdf.fonttype": 42, "ps.fonttype": 42,
                     "savefig.bbox": "standard"})   # the superiority module sets a tight bbox on import; keep the exact canvas
ROOT = "/home/kmanojp/oranslice_rig/experiments/results"
FIG = "/home/kmanojp/oranslice_rig/Papers_4-5/Paper_5/WPC/figures"
OUT = f"{FIG}/fig_capability"
AX_C, INK, PALE, GREY = "#0072B2", "#3a3a3a", "#e3eef7", "#555555"
LEARNED = ("single_agent_dqn", "independent_dqn", "mappo_tuned")
DELAY_OK = 0.5      # control periods of mean URLLC backlog delay at 37 gNBs
SLA_OK = 90.0       # Env A priority-slice compliance at 37 gNBs, percent


def m77_delay(arm):
    v = []
    for f in glob.glob(f"{ROOT}/m77/A_n37_hex/{arm}_*.json"):
        for r in json.load(open(f)).values():
            x = r["kpi"]["urllc"]["delay_steps"]
            if x is not None:
                v.append(x)
    return float(np.mean(v))


def data():
    cx = json.load(open(f"{ROOT}/m64/complexity.json")); c37 = json.load(open(f"{ROOT}/m73/complexity_n37.json"))["37"]
    par = {a: [cx[str(n)][k]["params_execution"] for n in (3, 7, 19)] + [c37[k]["params_execution"]]
           for a, k in (("axiom2", "axiom2"), ("mappo_tuned", "mappo"), ("single_agent_dqn", "single_agent_dqn"), ("independent_dqn", "independent_dqn"))}
    m92 = json.load(open(f"{ROOT}/m92/analysis.json"))["cells"]
    tr_ax = [m92[f"A_{t}_n37"]["AXIOM-7to37"]["prio"]["mean"] for t in ("hex", "ring", "fully_connected")]
    tr_mp = m92["A_hex_n37"]["MAPPO-7to37"]["prio"]["mean"]
    ax37 = [r for t, ss in (("hex", S30_19), ("ring", S15), ("fully_connected", S15)) for r in seeds_of(f"m73/A_n37_{t}", "axiom2", ss).values()]
    sla = {"axiom2": 100 * float(np.mean([prio(r) for r in ax37]))}
    for a in LEARNED + ("rule_static",):
        sla[a] = 100 * float(np.mean([prio(r) for r in seeds_of("m73/A_n37_hex", a, S30_19).values()]))
    delay = {a: m77_delay(a) for a in ("axiom2",) + LEARNED + ("rule_static",)}
    rg = json.load(open(f"{FIG}/fig_regime_summary.json"))
    mean = lambda d: float(np.mean([r["reward"] for r in d.values()]))
    b3 = {a: mean(seeds_of("m64/n3_fully_connected", a, S30)) for a in ("axiom2", "mappo_tuned")}
    b19 = {a: mean(seeds_of("m75/D_envB_n19_hex", a, S15)) for a in ("axiom2", "mappo_tuned")}
    over_mappo = [100 * (b3["axiom2"] / b3["mappo_tuned"] - 1), 100 * (b19["axiom2"] / b19["mappo_tuned"] - 1)]
    over_rule = []
    for sh in ("load_1.10", "load_1.15", "load_1.20"):
        a = {s: {"reward": shift_row("m76/b1_shift_n19", sh, "axiom2", s)["reward"]} for s in S15}
        b = {s: {"reward": shift_row("m76/b1_shift_n19", sh, "rule_local_transfer", s)["reward"]} for s in S15}
        over_rule.append(paired(a, b)["diff"])
    return dict(params=par, transfer_axiom=tr_ax, transfer_mappo=tr_mp, sla37=sla, delay37=delay,
                past_B=[v["verdict"] for k, v in rg["B"].items() if float(k.split("|")[1]) >= 1.10],
                past_A=[v["verdict"] for k, v in rg["A"].items() if float(k.split("|")[1]) > 1.05],
                nominal_B=[v["verdict"] for k, v in rg["B"].items() if k.endswith("|1.00")],
                over_mappo_pct=over_mappo, over_tuned_rule=over_rule)


def matrix(d):
    P, T, S, D = d["params"], d["transfer_axiom"], d["sla37"], d["delay37"]
    fixed = lambda a: "full" if len(set(P[a])) == 1 else "none"
    sla = lambda a: "full" if S[a] >= SLA_OK else "none"
    dl = lambda a: "full" if D[a] < DELAY_OK else "none"
    past_ax = "full" if all(v == "AXIOM" for v in d["past_B"]) else "half"
    rows = [
        ("AXIOM", [(fixed("axiom2"), f"{P['axiom2'][-1]:,}"), ("full" if min(T) >= SLA_OK else "half", f"{min(T):.0f}–{max(T):.0f}%"),
                   (sla("axiom2"), f"{S['axiom2']:.1f}%"), ("full", ""), (dl("axiom2"), f"{D['axiom2']:.2f}"), (past_ax, "ahead"),
                   ("none", "loses"), ("full", "tested")]),
        ("MAPPO", [(fixed("mappo_tuned"), f"{P['mappo_tuned'][-1]:,}"), ("half" if d["transfer_mappo"] < SLA_OK else "full", f"{d['transfer_mappo']:.1f}%"),
                   (sla("mappo_tuned"), f"{S['mappo_tuned']:.1f}%"), ("full", ""), (dl("mappo_tuned"), f"{D['mappo_tuned']:.2f}"), ("na", ""),
                   ("none", "loses"), ("na", "")]),
        ("DQN-SA", [(fixed("single_agent_dqn"), f"{P['single_agent_dqn'][-1]:,}"), ("none", "cannot"), (sla("single_agent_dqn"), f"{S['single_agent_dqn']:.1f}%"),
                    ("full", ""), (dl("single_agent_dqn"), f"{D['single_agent_dqn']:.2f}"), ("na", ""), ("none", "loses"), ("na", "")]),
        ("DQN-I", [(fixed("independent_dqn"), f"{P['independent_dqn'][-1]:,}"), ("none", "cannot"), (sla("independent_dqn"), f"{S['independent_dqn']:.1f}%"),
                   ("full", ""), (dl("independent_dqn"), f"{D['independent_dqn']:.2f}"), ("na", ""), ("none", "loses"), ("na", "")]),
        ("Static rule", [("full", "none"), ("full", "any"), (sla("rule_static"), f"{S['rule_static']:.2f}%"), ("none", ""),
                         (dl("rule_static"), f"{D['rule_static']:.2f}"), ("half" if all(v == "tie" for v in d["past_A"]) else "none", "ties"),
                         ("full", "best"), ("na", "")]),
        ("Tuned rule", [("full", "none"), ("full", "7 to 19"), ("na", ""), ("none", ""), ("na", ""),
                        ("none" if all(v == "AXIOM" for v in d["past_B"]) else "half", "trails"),
                        ("full" if all(v == "rule" for v in d["nominal_B"]) else "half", "best"), ("na", "")]),
    ]
    return rows


def tiles(d):
    P, T, D, S = d["params"], d["transfer_axiom"], d["delay37"], d["sla37"]
    lead = S["axiom2"] - max(S[a] for a in LEARNED)
    rat = [D[a] / D["axiom2"] for a in LEARNED]
    om, orule = d["over_mappo_pct"], d["over_tuned_rule"]
    return [
        (f"{lead:.1f} points", "compliance lead over the best\nlearned baseline at 37 gNBs"),
        (f"{min(rat):.0f}–{max(rat):.0f}×", "shorter URLLC backlog delay\nthan the learned baselines"),
        (f"{P['independent_dqn'][-1] / P['axiom2'][-1]:.0f}×", "fewer parameters than\nDQN-I at 37 gNBs"),
        (f"{np.floor(min(T)):.0f}%+", "compliance when moved from\n7 to 37 gNBs, no retraining"),
        (f"+{max(orule):.1f}", "reward per step over the\ntuned rule past its load"),
        (f"{min(om):.0f}–{max(om):.0f}%", "more reward than MAPPO\nunder coupled load"),
    ]


def glyph(ax, x, y, kind, col, r=1.45):
    if kind == "full":
        ax.add_patch(Circle((x, y), r, fc=col, ec=col, lw=0.8))
    elif kind == "half":
        ax.add_patch(Circle((x, y), r, fc="white", ec=col, lw=0.8))
        ax.add_patch(Wedge((x, y), r, 90, 270, fc=col, ec=col, lw=0.8))
    elif kind == "none":
        ax.add_patch(Circle((x, y), r, fc="white", ec=col, lw=0.8))
    else:
        ax.plot([x - r * 0.8, x + r * 0.8], [y, y], color="#9a9a9a", lw=1.0)


def draw(rows, tl):
    W, H = 119.0, 99.0
    fig = plt.figure(figsize=(W / 25.4, H / 25.4))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")
    heads = ["Fixed\nsize", "New\nsize", "SLA at\n37 gNBs", "Learns\nrules", "URLLC\ndelay", "Past\ntuning", "Steady\nload", "Private\ntraining"]
    x0, dx = 17.5, 10.7
    xs = x0 + 8 * dx + 0.6
    ytop, dy = 88.5, 8.0
    for j, h in enumerate(heads):
        ax.text(x0 + dx * (j + 0.5), ytop + 5.6, h, ha="center", va="center", fontsize=8, color=INK, linespacing=1.0)
    ax.text(xs + 7.4, ytop + 5.6, "Criteria\nmet", ha="center", va="center", fontsize=8, color=INK, linespacing=1.0)
    for i, (name, cells) in enumerate(rows):
        y = ytop - dy * (i + 0.5)
        isax = i == 0
        if isax:
            ax.add_patch(FancyBboxPatch((0.8, y - dy / 2 + 0.35), W - 1.6, dy - 0.7, boxstyle="round,pad=0,rounding_size=1.5",
                                        fc=PALE, ec=AX_C, lw=1.0))
        if i == 4:
            ax.plot([1.0, W - 1.0], [y + dy / 2, y + dy / 2], color="#b5b5b5", lw=0.6, ls=(0, (3, 2)))
        ax.text(1.8, y, name, ha="left", va="center", fontsize=8, color=AX_C if isax else INK)
        for j, (kind, lab) in enumerate(cells):
            cx = x0 + dx * (j + 0.5)
            glyph(ax, cx, y + 1.15 if lab else y, kind, AX_C if isax else GREY)
            if lab:
                ax.text(cx, y - 2.3, lab, ha="center", va="center", fontsize=8, color=INK)
        score = sum(1.0 if k == "full" else 0.5 if k == "half" else 0.0 for k, _ in cells)
        ax.add_patch(FancyBboxPatch((xs + 0.6, y - 1.4), 6.0, 2.8, boxstyle="round,pad=0,rounding_size=0.5", fc="#e6e6e6", ec="none"))
        if score:
            ax.add_patch(FancyBboxPatch((xs + 0.6, y - 1.4), 6.0 * score / 8, 2.8, boxstyle="round,pad=0,rounding_size=0.5",
                                        fc=AX_C if isax else "#8c8c8c", ec="none"))
        ax.text(xs + 7.4, y, f"{score:g}/8", ha="left", va="center", fontsize=8, color=AX_C if isax else INK)
    ly = ytop - dy * 6 - 3.0
    lx = 12.0
    for kind, lab in (("full", "meets"), ("half", "partly"), ("none", "does not"), ("na", "not tested")):
        glyph(ax, lx, ly, kind, GREY, r=1.3)
        ax.text(lx + 2.4, ly, lab, va="center", fontsize=8, color=INK)
        lx += 25.0
    ty = ly - 5.0
    ax.text(1.8, ty, "AXIOM by the numbers", ha="left", va="center", fontsize=8, color=AX_C)
    tw, th, gap = (W - 1.6 - 2 * 1.4) / 3, 13.2, 1.4
    for k, (big, lab) in enumerate(tl):
        c, r = k % 3, k // 3
        bx, by = 0.8 + c * (tw + gap), ty - 2.6 - (r + 1) * th - r * gap
        ax.add_patch(FancyBboxPatch((bx, by), tw, th, boxstyle="round,pad=0,rounding_size=1.4", fc=PALE, ec="none"))
        ax.text(bx + tw / 2, by + th - 3.6, big, ha="center", va="center", fontsize=12.5, color=AX_C)
        ax.text(bx + tw / 2, by + 3.9, lab, ha="center", va="center", fontsize=8, color=INK, linespacing=1.05)
    fig.savefig(OUT + ".pdf", bbox_inches=None); fig.savefig(OUT + ".png", dpi=220, bbox_inches=None)   # exact 119 mm canvas


if __name__ == "__main__":
    d = data()
    rows, tl = matrix(d), tiles(d)
    draw(rows, tl)
    json.dump({"data": d, "rows": [[n, c] for n, c in rows], "tiles": tl, "thresholds": {"sla37": SLA_OK, "delay37": DELAY_OK}},
              open(OUT + "_summary.json", "w"), indent=1)
    for n, c in rows:
        print(f"{n:12s}", " | ".join(f"{k:4s} {l}" for k, l in c))
    for t in tl:
        print(t[0], "-", t[1].replace("\n", " "))
