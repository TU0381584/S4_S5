"""Fig: what each controller offers (top) and AXIOM's main margins (bottom), main paper, Discussion.

Top, a matrix of eight criteria. A criterion is met (filled), partly met (half), not met (open), or not tested (dash)
by the fixed rules in matrix(). Bottom, six margins of AXIOM. Every value is computed here from stored results:
execution parameters from the complexity records (m64 at 3, 7 and 19 gNBs, m73 at 37), transfer from seven gNBs
from M92, Env A compliance and URLLC backlog delay at 37 gNBs from the scaling cells and the M77 recorder, behaviour
past and at the rules' tuning load from the regime map's summary (AXIOM, rules) and from M96 b (learned baselines), Env B reward against MAPPO from the reported cells,
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
from matplotlib.patches import FancyBboxPatch  # noqa: E402

sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/scripts")
sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/plots")
from m66_verify import S15, S30, S30_19, holm, prio, seeds_of, paired  # noqa: E402
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


def past_tuning():
    """M96 b (Env B, stored checkpoints): each learned controller against the tuned rule at 110, 115 and 120% load at
    3, 7 and 19 gNBs, Holm over those nine tests per controller. Returns how many of the nine it wins significantly."""
    cells = {3: ("m96/B_shift/n3", list(range(905, 930)), "rule_local"), 7: ("m96/B_shift/n7_ring", S15, "rule_local"),
             19: ("m96/B_shift/n19_hex", S15, "rule_local_transfer")}
    out = {}
    for arm in ("axiom2",) + LEARNED:
        t = {}
        for n, (c, ss, rule) in cells.items():
            for L in ("load_1.10", "load_1.15", "load_1.20"):
                t[f"{n}|{L}"] = paired(seeds_of(f"{c}/{L}", arm, ss), seeds_of(f"{c}/{L}", rule, ss))
        h = holm({k: v["p"] for k, v in t.items()})
        out[arm] = {"wins": sum(v["diff"] > 0 and h[k] < 0.05 for k, v in t.items()), "tests": len(t),
                    "n": sorted({v["n"] for v in t.values()})}
    return out


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
                over_mappo_pct=over_mappo, over_tuned_rule=over_rule, past_learned=past_tuning())


def matrix(d):
    P, T, S, D = d["params"], d["transfer_axiom"], d["sla37"], d["delay37"]
    fixed = lambda a: "full" if len(set(P[a])) == 1 else "none"
    sla = lambda a: "full" if S[a] >= SLA_OK else "none"
    dl = lambda a: "full" if D[a] < DELAY_OK else "none"
    past_ax = "full" if all(v == "AXIOM" for v in d["past_B"]) else "half"
    PL = d["past_learned"]
    pl = lambda a: ("full", "ahead") if PL[a]["wins"] == PL[a]["tests"] else ("half", "mixed") if PL[a]["wins"] else ("none", "trails")
    assert pl("axiom2")[0] == past_ax, "M96 and the regime map disagree on AXIOM past the tuning load"
    rows = [
        ("AXIOM", [(fixed("axiom2"), f"{P['axiom2'][-1]:,}"), ("full" if min(T) >= SLA_OK else "half", f"{min(T):.0f}–{max(T):.0f}%"),
                   (sla("axiom2"), f"{S['axiom2']:.1f}%"), ("full", ""), (dl("axiom2"), f"{D['axiom2']:.2f}"), (past_ax, "ahead"),
                   ("none", "loses"), ("full", "tested")]),
        ("MAPPO", [(fixed("mappo_tuned"), f"{P['mappo_tuned'][-1]:,}"), ("half" if d["transfer_mappo"] < SLA_OK else "full", f"{d['transfer_mappo']:.1f}%"),
                   (sla("mappo_tuned"), f"{S['mappo_tuned']:.1f}%"), ("full", ""), (dl("mappo_tuned"), f"{D['mappo_tuned']:.2f}"), pl("mappo_tuned"),
                   ("none", "loses"), ("na", "")]),
        ("DQN-SA", [(fixed("single_agent_dqn"), f"{P['single_agent_dqn'][-1]:,}"), ("none", "cannot"), (sla("single_agent_dqn"), f"{S['single_agent_dqn']:.1f}%"),
                    ("full", ""), (dl("single_agent_dqn"), f"{D['single_agent_dqn']:.2f}"), pl("single_agent_dqn"), ("none", "loses"), ("na", "")]),
        ("DQN-I", [(fixed("independent_dqn"), f"{P['independent_dqn'][-1]:,}"), ("none", "cannot"), (sla("independent_dqn"), f"{S['independent_dqn']:.1f}%"),
                   ("full", ""), (dl("independent_dqn"), f"{D['independent_dqn']:.2f}"), pl("independent_dqn"), ("none", "loses"), ("na", "")]),
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


# Status encoding, one sequential blue scale that also reads in greyscale: dark meets, light partly, white does not,
# grey not tested. Layout follows the summary matrices of benchmarking papers: criteria grouped under category headers,
# one tile per controller and criterion with its value inside, the overall score as bars, hairlines instead of boxes.
FILL = {"full": "#0072B2", "half": "#a8cdea", "none": "#ffffff", "na": "#ececec"}
TXT = {"full": "#ffffff", "half": INK, "none": INK, "na": "#8a8a8a"}
EDGE = {"full": "#0072B2", "half": "#a8cdea", "none": "#9fb6c9", "na": "#ececec"}
RULE = "#c8c8c8"
GROUPS = [("Scale", [(0, "Fixed size"), (1, "New size")]),
          ("Service at 37 gNBs", [(2, "Priority SLA"), (4, "URLLC delay")]),
          ("Adaptation", [(3, "Learns its rules"), (5, "Past tuning load"), (6, "Steady load")]),
          ("Privacy", [(7, "Private training")])]


def tile(ax, cx, cy, w, h, kind, lab):
    ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h, boxstyle="round,pad=0,rounding_size=1.0",
                                fc=FILL[kind], ec=EDGE[kind], lw=0.7, zorder=3))
    txt = lab if lab else {"na": "\u2013", "full": "yes", "none": "no"}.get(kind, "")
    if txt:
        ax.text(cx, cy, txt, ha="center", va="center", fontsize=8, color=TXT[kind], zorder=4)


def draw(rows, tl):
    W, H = 119.0, 124.6
    fig = plt.figure(figsize=(W / 25.4, H / 25.4))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")
    names = [n for n, _ in rows]
    x0, cw = 29.0, (W - 1.0 - 29.0) / len(rows)
    cx = [x0 + cw * (j + 0.5) for j in range(len(rows))]
    tw, th, rh, gh = cw - 1.4, 4.7, 5.6, 4.2
    # column headers: controller families, then names
    y = H - 2.6
    for lab, js in (("Learned controllers", range(0, 4)), ("Rules", range(4, 6))):
        xa, xb = cx[js[0]] - tw / 2, cx[js[-1]] + tw / 2
        ax.text((xa + xb) / 2, y, lab, ha="center", va="center", fontsize=8, color="#6a6a6a")
        ax.plot([xa, xb], [y - 2.2, y - 2.2], color=RULE, lw=0.6)
    y_name = y - 5.6
    for j, n in enumerate(names):
        ax.text(cx[j], y_name, n, ha="center", va="center", fontsize=8, color=AX_C if j == 0 else INK)
    ax.plot([1.0, W - 1.0], [y_name - 3.0, y_name - 3.0], color=INK, lw=0.7)
    # criteria, grouped under category headers
    y = y_name - 3.0
    body_top = y
    for g, crit in GROUPS:
        ax.text(1.0, y - gh / 2 - 0.1, g, ha="left", va="center", fontsize=8, color="#6a6a6a")
        y -= gh
        for k, lab in crit:
            ax.text(3.0, y - rh / 2, lab, ha="left", va="center", fontsize=8, color=INK)
            for j, (_, cells) in enumerate(rows):
                kind, val = cells[k]
                tile(ax, cx[j], y - rh / 2, tw, th, kind, val)
            y -= rh
        y -= 0.7
        ax.plot([1.0, W - 1.0], [y, y], color=RULE, lw=0.5)
    # overall score as bars, out of 8
    sc = [sum(1.0 if k == "full" else 0.5 if k == "half" else 0.0 for k, _ in cells) for _, cells in rows]
    base, hmax = y - 10.4, 6.6
    ax.text(1.0, base + hmax + 1.7, "Criteria met", ha="left", va="center", fontsize=8, color=INK)
    ax.text(3.0, base + 2.4, "out of 8", ha="left", va="center", fontsize=8, color="#6a6a6a")
    for j, v in enumerate(sc):
        bw = tw * 0.55
        ax.add_patch(plt.Rectangle((cx[j] - bw / 2, base), bw, hmax, fc="#f1f1f1", ec="none", zorder=2))
        ax.add_patch(plt.Rectangle((cx[j] - bw / 2, base), bw, hmax * v / 8, fc=AX_C if j == 0 else "#8c8c8c", ec="none", zorder=3))
        ax.text(cx[j], base + hmax + 1.7, f"{v:g}", ha="center", va="center", fontsize=8, color=AX_C if j == 0 else INK)
    ax.plot([1.0, W - 1.0], [base - 0.0, base - 0.0], color=INK, lw=0.7)
    # AXIOM's column, highlighted from its name to its bar
    ax.add_patch(FancyBboxPatch((cx[0] - cw / 2 + 0.2, base - 1.0), cw - 0.4, y_name + 3.4 - base + 1.0,
                                boxstyle="round,pad=0,rounding_size=1.2", fc=PALE, ec="none", zorder=1))
    # learned against rules
    xs = (cx[3] + cx[4]) / 2
    ax.plot([xs, xs], [base, body_top + 7.6], color=RULE, lw=0.6, ls=(0, (2, 1.5)), zorder=2)
    # legend
    ly = base - 4.6
    lx = 6.0
    for kind, lab in (("full", "meets"), ("half", "partly"), ("none", "does not"), ("na", "not tested")):
        ax.add_patch(FancyBboxPatch((lx, ly - 1.6), 5.0, 3.2, boxstyle="round,pad=0,rounding_size=0.7",
                                    fc=FILL[kind], ec=EDGE[kind], lw=0.7))
        ax.text(lx + 6.6, ly, lab, ha="left", va="center", fontsize=8, color=INK)
        lx += 28.0
    # AXIOM by the numbers: key figures separated by hairlines
    ty = ly - 5.4
    ax.text(1.0, ty, "AXIOM by the numbers", ha="left", va="center", fontsize=8, color=AX_C)
    ax.plot([34.0, W - 1.0], [ty, ty], color=RULE, lw=0.6)
    sw, sh = (W - 2.0) / 3, 11.8
    for k, (big, lab) in enumerate(tl):
        c, r = k % 3, k // 3
        bx, by = 1.0 + c * sw, ty - 3.0 - (r + 1) * sh
        ax.text(bx + sw / 2, by + sh - 2.9, big, ha="center", va="center", fontsize=12.5, color=AX_C)
        ax.text(bx + sw / 2, by + 3.3, lab, ha="center", va="center", fontsize=8, color=INK, linespacing=1.05)
        if c:
            ax.plot([bx, bx], [by + 1.2, by + sh - 1.2], color=RULE, lw=0.6)
    ax.plot([1.0, W - 1.0], [ty - 3.0 - sh, ty - 3.0 - sh], color=RULE, lw=0.5)
    print("lowest y", round(ty - 3.0 - 2 * sh, 2))
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
