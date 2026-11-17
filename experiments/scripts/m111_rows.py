#!/usr/bin/env python3
"""Table rows for the M111 pooling (docs/PAPER5_M111_preregistration.md): rewrites the data rows of the paper's tables
that depend on the Env A samples, from the stored logs through m66_verify's reader. Run from framework/:
  ../venv/bin/python ../experiments/scripts/m111_rows.py --main ../Papers_4-5/Paper_5/WPC/main.tex --supp ../Papers_4-5/Paper_5/WPC/supplementary.tex
Rows are replaced in place, in the order they appear; every number is also recomputed independently by m66_verify.py."""
import argparse, os, re, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m66_verify as V
from m66_verify import S30, mean, paired, prio, seeds_of

rng = np.random.default_rng(12345)


def ci(vals):
    v = np.asarray(vals); bm = v[rng.integers(0, len(v), size=(10000, len(v)))].mean(axis=1)
    return np.percentile(bm, 2.5), np.percentile(bm, 97.5)


def t3_rows():
    A = {a: seeds_of("m65_reviewer/base", a, S30) for a in ("axiom2", "mappo_tuned")}
    for a in ("heuristic", "single_agent_dqn", "independent_dqn"):
        A[a] = seeds_of("m63_reviewer/base", a, S30)
    nm = {"heuristic": "Static rule", "axiom2": "AXIOM", "single_agent_dqn": "DQN-SA", "independent_dqn": "DQN-I", "mappo_tuned": "MAPPO"}
    out = {}
    for a, n in nm.items():
        r = A[a]; lo, hi = ci([x["reward"] for x in r.values()])
        prec = [x["precision"] for x in r.values() if x["precision"] is not None]
        wtl = "--" if a == "axiom2" else "{}/{}/{}".format(*[paired(A["axiom2"], r)[k] for k in ("wins", "ties", "losses")])
        out[n] = (f"{n} & {mean(r):.3f} & [{lo:.2f}, {hi:.2f}] & {100 * mean(r) / mean(A['heuristic']):.1f} & {wtl} & {np.mean(prec):.3f} & "
                  f"{sum(x['collapsed'] for x in r.values())}/{len(r)} & {100 * mean(r, lambda x: x['sla']['urllc']):.1f} & "
                  f"{100 * mean(r, lambda x: x['sla']['embb']):.1f} & {100 * mean(r, lambda x: x['sla']['mmtc']):.1f} \\\\")
    return out


def replace_rows(tex, label, new_rows, keys=None):
    """Replace, inside the table that holds \\label{label}, the data rows whose first cell is a key, in order."""
    k = tex.index("\\label{%s}" % label); a = tex.rindex("\\begin{table}", 0, k); b = tex.index("\\end{table}", k)
    t = tex[a:b]; lines = t.split("\n"); it = iter(new_rows)
    for i, l in enumerate(lines):
        if l.endswith("\\\\") and " & " in l and not l.startswith(("Policy", "&", "\\multicolumn", "Env", "Setting", "Checkpoint")):
            if keys is not None and l.split(" & ")[0].strip() not in keys:
                continue
            try:
                lines[i] = next(it)
            except StopIteration:
                raise SystemExit(f"{label}: more table rows than new rows")
    assert next(it, None) is None, f"{label}: fewer table rows than new rows"
    return tex[:a] + "\n".join(lines) + tex[b:]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--main", required=True); ap.add_argument("--supp", required=True); a = ap.parse_args()
    main_tex, supp = open(a.main).read(), open(a.supp).read()
    rows = t3_rows()
    main_tex = replace_rows(main_tex, "tab:m2-results", [rows[k] for k in ("Static rule", "AXIOM", "DQN-SA", "DQN-I", "MAPPO")])
    g = "../experiments/results/gate3"
    eff = [l for l in open(f"{g}/table_main_rows.tex").read().replace("%%\n", "").split("\n") if l.strip()]
    supp = replace_rows(supp, "tab:effects", eff)
    sp = [l for l in open(f"{g}/table_supp_rows.tex").read().replace("%%\n", "").split("\n") if l.strip()]
    supp = replace_rows(supp, "tab:s-split", sp)
    supp = replace_rows(supp, "tab:s-new", new_seed_rows())
    open(a.main, "w").write(main_tex); open(a.supp, "w").write(supp)
    print("rows replaced")


def fmt_p(p):
    return "$<$0.0001" if p < 1e-4 else (f"{p:.4f}" if p < 0.01 else (f"{p:.3f}" if p < 0.1 else f"{p:.2f}"))


def fmt_s(x, nd):
    return f"{x:.{nd}f}".replace("-", "$-$")


def new_seed_rows():
    """Rows of OR1 Table tab:s-new from experiments/results/m111/analysis.json (the 15 newest seeds alone)."""
    import json
    a = json.load(open("../experiments/results/m111/analysis.json")); t = a["A3_table3"]["new"]
    nm = [("single_agent_dqn", "DQN-SA"), ("independent_dqn", "DQN-I"), ("mappo_tuned", "MAPPO"), ("axiom2_mlp", "MLP encoder"), ("rule_static", "Static rule")]
    rows = [f"{n} & {fmt_s(t[k + '|reward']['diff'], 3)} & {fmt_p(t[k + '|reward']['p_holm'])} & {fmt_s(t[k + '|compliance']['diff'], 1)} & {fmt_p(t[k + '|compliance']['p_holm'])} \\\\" for k, n in nm]
    for s, n in (("A7_scaling", 7), ("A19_scaling", 19), ("A37_scaling", 37)):
        c = {k: v for k, v in a[s]["new"].items() if k.endswith("compliance")}
        kmin = min(c, key=lambda x: c[x]["diff"])
        rows.append(f"{n} gNBs & & & {fmt_s(c[kmin]['diff'], 1)} & {fmt_p(max(v['p_holm'] for v in c.values()))} \\\\")
    return rows
