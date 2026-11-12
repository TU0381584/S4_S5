#!/usr/bin/env python3
"""M107 runner (docs/PAPER5_M107_preregistration.md): the seed extension of the cells plotted in Figs. 5 and 7.

Every arm runs exactly as in its original campaign (m64_run.py, or m73_run.py at 37 gNBs, with M63_BACKLOG_RESET=1
and M64_AXIOM_V2=1), with one difference for the tuned rules: rule_local and rule_neighbour are not re-tuned on the
new seeds. They apply, unchanged, the rule that the original campaign selected on its training streams, read from
M107_RULE_SELECTION (a <arm>_selection.json file), so pooled seeds share one tuned rule. Without that variable this
runner is m64_run.py (or m73_run.py with --n 37).
Usage (cwd framework/): m107_run.py <m64_run.py arguments>
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m64_run  # noqa: E402


def fixed_rules(orig):
    sel = os.environ.get("M107_RULE_SELECTION")

    def run_rules(arm, cfg, factory, nbrs, seeds, out_dir):
        if not sel or arm not in ("rule_local", "rule_neighbour"):
            return orig(arm, cfg, factory, nbrs, seeds, out_dir)
        stored = json.load(open(sel))
        assert os.path.basename(sel) == f"{arm}_selection.json", (sel, arm)
        rule = stored["selected"]
        print(f"[m107:{arm}] stored rule {rule} from {sel}, not re-tuned", flush=True)
        out = {}
        for s in seeds:
            m64_run.clear(out_dir, arm, s)
            p = m64_run.rule_eval(cfg, factory, rule, nbrs, m64_run.EVAL_OFFSET + s, 50, f"{out_dir}/{arm}/seed{s}/eval", "offline_eval")
            out[s] = m64_run.per_seed_metrics(p)[0]
        json.dump({"selected": rule, "source": sel, "retuned": False}, open(f"{out_dir}/{arm}_selection.json", "w"), indent=1)
        return rule, out
    return run_rules


if __name__ == "__main__":
    if "--n" in sys.argv and sys.argv[sys.argv.index("--n") + 1] == "37":
        import m73_run
        m73_run.install()
    m64_run.run_rules = fixed_rules(m64_run.run_rules)
    m64_run.main()
