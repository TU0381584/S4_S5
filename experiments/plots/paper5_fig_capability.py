"""Fig: what each controller offers, as a matrix of six criteria (main paper, Discussion).

Every value is computed here from stored results: execution parameters from the complexity records (m64 at 3, 7
and 19 gNBs, m73 at 37), transfer from seven gNBs from M92, Env A priority-slice compliance at 37 gNBs from the
cells of the main paper's scaling results, and behaviour past the rules' tuning load from Fig. regime's summary.
A criterion is met (filled), partly met (half), not met (open), or not tested (dash) by fixed rules written below.
Every value and verdict is saved to <out>_summary.json, which m66_verify recomputes.
"""
import json
import sys

import numpy as np
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, FancyBboxPatch, Wedge  # noqa: E402

sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/scripts")
from m66_verify import S15, S30_19, prio, seeds_of  # noqa: E402

mpl.rcParams.update({"font.size": 8, "pdf.fonttype": 42, "ps.fonttype": 42})
ROOT = "/home/kmanojp/oranslice_rig/experiments/results"
FIG = "/home/kmanojp/oranslice_rig/Papers_4-5/Paper_5/WPC/figures"
OUT = f"{FIG}/fig_capability"
AX_C, INK, PALE = "#0072B2", "#3a3a3a", "#e3eef7"


def data():
    cx = json.load(open(f"{ROOT}/m64/complexity.json")); c37 = json.load(open(f"{ROOT}/m73/complexity_n37.json"))["37"]
    par = {a: [cx[str(n)][a]["params_execution"] for n in (3, 7, 19)] + [c37[a]["params_execution"]]
           for a in ("axiom2", "single_agent_dqn", "independent_dqn")}
    par["mappo_tuned"] = [cx[str(n)]["mappo"]["params_execution"] for n in (3, 7, 19)] + [c37["mappo"]["params_execution"]]
    m92 = json.load(open(f"{ROOT}/m92/analysis.json"))["cells"]
    tr_ax = [m92[f"A_{t}_n37"]["AXIOM-7to37"]["prio"]["mean"] for t in ("hex", "ring", "fully_connected")]
    tr_mp = m92["A_hex_n37"]["MAPPO-7to37"]["prio"]["mean"]
    ax37 = [r for t, ss in (("hex", S30_19), ("ring", S15), ("fully_connected", S15)) for r in seeds_of(f"m73/A_n37_{t}", "axiom2", ss).values()]
    sla = {"axiom2": 100 * float(np.mean([prio(r) for r in ax37]))}
    for a in ("single_agent_dqn", "independent_dqn", "mappo_tuned", "rule_static"):
        sla[a] = 100 * float(np.mean([prio(r) for r in seeds_of("m73/A_n37_hex", a, S30_19).values()]))
    rg = json.load(open(f"{FIG}/fig_regime_summary.json"))
    past_B = [v["verdict"] for k, v in rg["B"].items() if float(k.split("|")[1]) >= 1.10]
    past_A = [v["verdict"] for k, v in rg["A"].items() if float(k.split("|")[1]) > 1.05]
    nom_B = [v["verdict"] for k, v in rg["B"].items() if k.endswith("|1.00")]
    return dict(params=par, transfer_axiom=tr_ax, transfer_mappo=tr_mp, sla37=sla, past_B=past_B, past_A=past_A, nominal_B=nom_B)


def matrix(d):
    P, T, S = d["params"], d["transfer_axiom"], d["sla37"]
    fixed = lambda a: len(set(P[a])) == 1
    k = lambda x: f"{x / 1000:.0f}k"
    ok90 = lambda v: "full" if v >= 90 else "none"
    ax_past = "full" if all(v == "AXIOM" for v in d["past_B"]) else "half"
    st_past = "half" if all(v == "tie" for v in d["past_A"]) else "none"
    tu_past = "none" if all(v == "AXIOM" for v in d["past_B"]) else "half"
    tu_nom = "full" if all(v == "rule" for v in d["nominal_B"]) else "half"
    rows = [
        ("AXIOM (proposed)", [("full" if fixed("axiom2") else "none", f"{P['axiom2'][0]:,}"),
                              ("full" if min(T) >= 90 else "half", f"{min(T):.0f}–{max(T):.0f}%"),
                              (ok90(S["axiom2"]), f"{S['axiom2']:.1f}%"), ("full", "learned"),
                              (ax_past, "ahead"), ("none", "rule wins")]),
        ("MAPPO", [("full" if fixed("mappo_tuned") else "none", f"{P['mappo_tuned'][0]:,}"),
                   ("half" if d["transfer_mappo"] < 90 else "full", f"{d['transfer_mappo']:.1f}%"),
                   (ok90(S["mappo_tuned"]), f"{S['mappo_tuned']:.1f}%"), ("full", "learned"), ("na", ""), ("none", "rule wins")]),
        ("DQN-SA", [("none" if not fixed("single_agent_dqn") else "full", f"{k(P['single_agent_dqn'][0])}–{k(P['single_agent_dqn'][-1])}"),
                    ("none", "cannot"), (ok90(S["single_agent_dqn"]), f"{S['single_agent_dqn']:.1f}%"),
                    ("full", "learned"), ("na", ""), ("none", "rule wins")]),
        ("DQN-I", [("none" if not fixed("independent_dqn") else "full", f"{k(P['independent_dqn'][0])}–{k(P['independent_dqn'][-1])}"),
                   ("none", "cannot"), (ok90(S["independent_dqn"]), f"{S['independent_dqn']:.1f}%"),
                   ("full", "learned"), ("na", ""), ("none", "rule wins")]),
        ("Static rule", [("full", "no model"), ("full", "size-free"), (ok90(S["rule_static"]), f"{S['rule_static']:.2f}%"),
                         ("none", "fixed slice"), (st_past, "ties"), ("full", "best")]),
        ("Tuned rule", [("full", "no model"), ("full", "7 to 19"), ("na", ""), ("none", "grid search"), (tu_past, "trails"), (tu_nom, "best")]),
    ]
    return rows


def glyph(ax, x, y, kind, col, r=1.55):
    if kind == "full":
        ax.add_patch(Circle((x, y), r, fc=col, ec=col, lw=0.8))
    elif kind == "half":
        ax.add_patch(Circle((x, y), r, fc="white", ec=col, lw=0.8))
        ax.add_patch(Wedge((x, y), r, 90, 270, fc=col, ec=col, lw=0.8))
    elif kind == "none":
        ax.add_patch(Circle((x, y), r, fc="white", ec=col, lw=0.8))
    else:
        ax.plot([x - r * 0.8, x + r * 0.8], [y, y], color="#9a9a9a", lw=1.0)


def draw(rows):
    W, H = 119.0, 74.0
    fig = plt.figure(figsize=(W / 25.4, H / 25.4))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")
    heads = ["Fixed\nsize", "Runs at\nnew size", "SLA at\n37 gNBs", "Learns\nits rules", "Past\ntuning", "Steady\nload"]
    x0, dx = 23.5, 12.4
    xs = x0 + 6 * dx + 1.0
    ytop, dy = 60.0, 8.3
    for j, h in enumerate(heads):
        ax.text(x0 + dx * (j + 0.5), ytop + 7.2, h, ha="center", va="center", fontsize=8, color=INK, linespacing=1.0)
    ax.text(xs + 10.0, ytop + 7.2, "Criteria\nmet", ha="center", va="center", fontsize=8, color=INK, linespacing=1.0)
    for i, (name, cells) in enumerate(rows):
        y = ytop - dy * (i + 0.5)
        isax = i == 0
        if isax:
            ax.add_patch(FancyBboxPatch((1.0, y - dy / 2 + 0.4), W - 2.0, dy - 0.8, boxstyle="round,pad=0,rounding_size=1.6",
                                        fc=PALE, ec=AX_C, lw=0.9))
        if i == 4:
            ax.plot([1.5, W - 1.5], [y + dy / 2, y + dy / 2], color="#b5b5b5", lw=0.6, ls=(0, (3, 2)))
        ax.text(2.0, y, name, ha="left", va="center", fontsize=8, color=AX_C if isax else INK)
        for j, (kind, lab) in enumerate(cells):
            cx = x0 + dx * (j + 0.5)
            glyph(ax, cx, y + 1.25, kind, AX_C if isax else "#555555")
            if lab:
                ax.text(cx, y - 2.35, lab, ha="center", va="center", fontsize=8 if len(lab) <= 9 else 7.5, color=INK)
        score = sum(1.0 if k == "full" else 0.5 if k == "half" else 0.0 for k, _ in cells)
        bw = 8.0 * score / 6
        ax.add_patch(FancyBboxPatch((xs + 1.0, y - 1.5), 8.0, 3.0, boxstyle="round,pad=0,rounding_size=0.6", fc="#e6e6e6", ec="none"))
        if bw > 0:
            ax.add_patch(FancyBboxPatch((xs + 1.0, y - 1.5), bw, 3.0, boxstyle="round,pad=0,rounding_size=0.6", fc=AX_C if isax else "#8c8c8c", ec="none"))
        ax.text(xs + 10.0, y, f"{score:g} of 6", ha="left", va="center", fontsize=8, color=AX_C if isax else INK)
    ly = 3.0
    items = [("full", "meets"), ("half", "partly"), ("none", "does not"), ("na", "not tested")]
    lx = 18.0
    for kind, lab in items:
        glyph(ax, lx, ly, kind, "#555555", r=1.35)
        ax.text(lx + 2.6, ly, lab, va="center", fontsize=8, color=INK)
        lx += 22.0
    fig.savefig(OUT + ".pdf"); fig.savefig(OUT + ".png", dpi=220)


if __name__ == "__main__":
    d = data()
    rows = matrix(d)
    draw(rows)
    json.dump({"data": d, "rows": [[n, c] for n, c in rows]}, open(OUT + "_summary.json", "w"), indent=1)
    for n, c in rows:
        print(f"{n:18s}", " | ".join(f"{k:4s} {l}" for k, l in c))
