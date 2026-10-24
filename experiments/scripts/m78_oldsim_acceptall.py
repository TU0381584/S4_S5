"""M78 audit: re-evaluate accept-all and the static rule in the original independent-slice simulator
(M2 KPM source), seeds 900-929, 50 held-out episodes each. Logs go to the given scratch dir; only
the per-seed summary is kept, in experiments/results/m78_oldsim/summary.json.
Usage (cwd = framework/): m78_oldsim_acceptall.py SCRATCH_DIR"""
import sys, json
sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/scripts")
import m64_run
import m2_run_experiment as m2
import coupled_dynamic_kpm_source as cd
from m66_verify import read
from qoe_oran_framework.config import load_saclb_config
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/m78_oldsim"
cfg = load_saclb_config(m64_run.CONFIGS[3])
sd = {k: v.sd for k, v in cfg.slice_by_id.items()}
factory = m2.make_kpm_source_factory(cfg, sd)
nbrs = cd.neighbour_lists(3, "fully_connected")
res = {}
for rule_name, rule in (("accept_all", dict()), ("static", dict(tau_c=0.0))):
    for s in range(900, 930):
        p = m64_run.rule_eval(cfg, factory, rule, nbrs, m64_run.EVAL_OFFSET + s, 50, f"{OUT}/{rule_name}/seed{s}", "offline_eval")
        r = read(p); res.setdefault(rule_name, {})[s] = {"reward": r["reward"], "sla": r["sla"], "blocks": r["blocks"]}
    v = list(res[rule_name].values())
    print(rule_name, "reward", sum(x["reward"] for x in v) / len(v), "urllc", sum(x["sla"]["urllc"] for x in v) / len(v),
          "embb", sum(x["sla"]["embb"] for x in v) / len(v), flush=True)
json.dump(res, open("/home/kmanojp/oranslice_rig/experiments/results/m78_oldsim/summary.json", "w"), indent=0)
