"""Fig: where learning beats a rule. One cell per tested cluster size and offered load.

Env A compares AXIOM's priority-slice compliance with the static rule, Env B its reward per gNB per step with
the tuned local rule, each paired per seed. The rules were tuned once at nominal load and are never re-tuned
here, and AXIOM is never retrained. A cell is filled by the sign of the mean paired difference when its
Wilcoxon signed-rank test survives Holm correction over that panel's cells (rule ahead also hatched), and neutral otherwise. Untested cells
stay blank; since M95 every cell is tested. The cells reuse the runs behind fig10_axiom_superiority (panels e, f) and the Env A results table. Every plotted number is written to
<out>_summary.json, which m66_verify recomputes.
"""
import json
import sys

import numpy as np
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Rectangle

sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/scripts")
sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/plots")
from m66_verify import S15, S30, S30_19, holm, paired, prio, seeds_of  # noqa: E402
from paper5_fig_superiority import LOAD_B, shift_row  # noqa: E402

sys.path.insert(0, "/home/kmanojp/oranslice_rig/Papers_4-5/Paper_5/WPC/figures")
import axiom_style as S  # noqa: E402
S.setup()
# figure audit: AXIOM ahead in blue and rule ahead in vermillion at 35% (pre-blended on white, so the EPS needs no
# transparency), rule ahead also hatched; no significant difference in a light neutral; values printed in every cell
AX_C, RULE_C, TIE_C = S.lighten("#0072B2", 0.15), S.lighten("#E69F00", 0.15), "#DDDDDD"   # pre-audit colours restored (2026-11-09), 85% pre-blended
LAYOUTS = ("fully_connected", "ring", "hex")
OUT = "../../Papers_4-5/Paper_5/WPC/figures/fig_regime"
EXTRA_B = {(7, "0.80"): ("m95/B_shift/n7_ring", "rule_local"), (7, "1.05"): ("m95/B_shift/n7_ring", "rule_local"),
           (7, "1.15"): ("m95/B_shift/n7_ring", "rule_local"), (19, "0.80"): ("m95/B_shift/n19", "rule_local_transfer"),
           (19, "1.05"): ("m95/B_shift/n19", "rule_local_transfer")}   # docs/PAPER5_M95_preregistration.md


def keyed(cell, arm, seeds, tag=""):
    return {(tag, s): r for s, r in seeds_of(cell, arm, seeds).items()}


def env_a_cells():
    """AXIOM against the static rule on priority-slice compliance, Env A, paired per layout and seed."""
    cells = {}
    ax3 = keyed("m65_reviewer/base", "axiom2", S30)
    st3 = keyed("m63_reviewer/base", "heuristic", S30)
    cells[(3, "1.05")] = (ax3, st3)
    for n, ss in ((7, S15), (19, S30_19)):
        ax, st = {}, {}
        for t in LAYOUTS:
            ax.update(keyed(f"m65_scaling/n{n}_{t}", "axiom2", ss, t))
            st.update(keyed(f"m70/R1/A_n{n}_{t}", "rule_static", ss, t))
        cells[(n, "1.05")] = (ax, st)
    cells[(37, "1.05")] = (keyed("m73/A_n37_hex", "axiom2", S30_19), keyed("m73/A_n37_hex", "rule_static", S30_19))
    for load in ("1.10", "1.20"):
        c = f"m76/e_load{load}_n19_hex"
        cells[(19, load)] = (keyed(c, "axiom2", S15), keyed(c, "rule_static", S15))
        for n, tag in ((3, "n3"), (7, "n7_hex"), (37, "n37_hex")):   # M95: the cells left blank before, run as M76 e was
            c = f"m95/A_load{load}_{tag}"
            cells[(n, load)] = (keyed(c, "axiom2", S15), keyed(c, "rule_static", S15))
    out = {k: paired(a, b, lambda r: 100 * prio(r)) for k, (a, b) in cells.items()}
    return out


def env_b_cells():
    """AXIOM against the tuned local rule on reward per gNB per step, Env B, under shifted load."""
    out = {}
    for n, (cell, rule, seeds, shifts) in LOAD_B.items():
        for sh in shifts:
            a = {s: {"reward": shift_row(cell, sh, "axiom2", s)["reward"] / n} for s in seeds}
            b = {s: {"reward": shift_row(cell, sh, rule, s)["reward"] / n} for s in seeds}
            load = "1.00" if sh == "nominal" else sh.split("_")[1]
            out[(n, load)] = paired(a, b)
    for (n, load), (cell, rule) in EXTRA_B.items():   # M95: the cells left blank before, evaluated as M72 and M76 b1 were
        sh = f"load_{load}"
        a = {s: {"reward": shift_row(cell, sh, "axiom2", s)["reward"] / n} for s in S15}
        b = {s: {"reward": shift_row(cell, sh, rule, s)["reward"] / n} for s in S15}
        out[(n, load)] = paired(a, b)
    return out


def classify(tests):
    h = holm({k: v["p"] for k, v in tests.items()})
    for k, v in tests.items():
        v["p_holm"] = h[k]
        v["verdict"] = ("AXIOM" if v["diff"] > 0 else "rule") if h[k] < 0.05 else "tie"
    return tests


def draw(ax, tests, sizes, loads, fmt, xlabel, nominal):
    for i, n in enumerate(sizes):
        for j, L in enumerate(loads):
            v = tests.get((n, L))
            y = len(sizes) - 1 - i
            if v is None:
                ax.add_patch(Rectangle((j, y), 1, 1, facecolor="white", edgecolor="#BBBBBB", lw=0.5, ls=(0, (2, 2))))
                continue
            fc = {"AXIOM": AX_C, "rule": RULE_C, "tie": TIE_C}[v["verdict"]]
            ax.add_patch(Rectangle((j, y), 1, 1, facecolor=fc, edgecolor="white", lw=1.2,
                                   hatch="////" if v["verdict"] == "rule" else None, hatchcolor="white"))
            if v["verdict"] == "rule":   # keep the printed value legible over the hatching
                ax.add_patch(Rectangle((j + 0.2, y + 0.3), 0.6, 0.4, facecolor=fc, edgecolor="none", zorder=3))
            ax.text(j + 0.5, y + 0.5, fmt(v["diff"]), ha="center", va="center", color="white" if v["verdict"] == "AXIOM" else S.INK, zorder=4)
    ax.set_xlim(0, len(loads))
    ax.set_ylim(0, len(sizes))
    ax.set_xticks([j + 0.5 for j in range(len(loads))])
    ax.set_xticklabels([f"{round(float(L) * 100)}" for L in loads])
    ax.set_yticks([len(sizes) - 1 - i + 0.5 for i in range(len(sizes))])
    ax.set_yticklabels([str(n) for n in sizes])
    ax.set_xlabel(xlabel)
    ax.set_ylabel("gNBs")
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    j0 = loads.index(nominal)
    ax.add_patch(Rectangle((j0, 0), 1, len(sizes), fill=False, edgecolor="black", lw=1.0, ls=(0, (3, 1.5)), zorder=5))


def main():
    A = classify(env_a_cells())
    B = classify(env_b_cells())
    H = 50.0   # compressed vertically (2026-11-10, author request): shorter cells, titles and legend set closer
    fig = S.figure("full", H)
    fw, fh = (lambda mm: mm / 119.0), (lambda mm: mm / H)
    axA = fig.add_axes([fw(9), fh(15), fw(30), fh(22.5)])
    axB = fig.add_axes([fw(56), fh(15), fw(61), fh(22.5)])
    mn = lambda s_: "0.00" if s_ in ("+0.00", "-0.00") else ("0.0" if s_ in ("+0.0", "-0.0") else s_.replace("-", "\u2212"))   # a difference that rounds to zero prints unsigned
    draw(axA, A, (3, 7, 19, 37), ("1.05", "1.10", "1.20"), lambda d: mn(f"{d:+.1f}"), "Offered load (%)", "1.05")
    draw(axB, B, (3, 7, 19), ("0.80", "1.00", "1.05", "1.10", "1.15", "1.20"), lambda d: mn(f"{d:+.2f}"),
         "Offered load (% of the rule\u2019s tuning load)", "1.00")
    for ax_ in (axA, axB):
        ax_.xaxis.labelpad = 2
    titles = (("AXIOM minus static rule,", "priority-slice compliance (pp)"), ("AXIOM minus tuned rule,", "reward per gNB per step"))
    for x_, t_, e_ in ((0.5, "a", "A"), (48, "b", "B")):
        fig.text(fw(x_), fh(H - 0.5), t_, fontweight="bold", va="top")
        S.env_badge(fig, fw(x_ + 3.5), fh(H - 0.5), e_, va="top")   # pre-audit badges restored (2026-11-09)
    for ax_, (l1_, l2_) in zip((axA, axB), titles):
        ax_.set_title(f"{l1_}\n{l2_}", loc="left", pad=2.5)
    handles = [Patch(facecolor=AX_C, label="AXIOM ahead"), Patch(facecolor=TIE_C, label="no significant difference"),
               Patch(facecolor=RULE_C, hatch="////", hatchcolor="white", label="rule ahead"),
               Patch(facecolor="white", edgecolor="#BBBBBB", ls=(0, (2, 2)), label="not run"),
               Patch(facecolor="white", edgecolor="black", ls=(0, (3, 1.5)), label="tuning load")]
    blank = any((n, L) not in A for n in (3, 7, 19, 37) for L in ("1.05", "1.10", "1.20")) or \
        any((n, L) not in B for n in (3, 7, 19) for L in ("0.80", "1.00", "1.05", "1.10", "1.15", "1.20"))
    if not blank:
        handles = [h for h in handles if h.get_label() != "not run"]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.0), ncol=4, frameon=False,
               handlelength=1.3, handletextpad=0.4, columnspacing=1.0)
    print(S.save(fig, OUT))
    summ = {env: {f"{n}|{L}": v for (n, L), v in T.items()} for env, T in (("A", A), ("B", B))}
    json.dump(summ, open(OUT + "_summary.json", "w"), indent=1)
    for env, T in (("A", A), ("B", B)):
        for (n, L), v in sorted(T.items()):
            print(env, n, L, f"n={v['n']} diff={v['diff']:+.3f} wins={v['wins']} ties={v['ties']} losses={v['losses']} "
                  f"p={v['p']:.4f} holm={v['p_holm']:.4f} {v['verdict']}")


if __name__ == "__main__":
    main()
