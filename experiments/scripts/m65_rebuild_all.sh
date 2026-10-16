#!/bin/bash
# Rebuild every M64 (Env B) and M65 (Env A, AXIOM v2) summary, test, and screen.
# Run from the repo root after experiments/logs/m64/full/progress.log reports "ALL B DONE".
# Figures are generated separately (see the paper5_* plot scripts), once these summaries exist.
set -u
cd /home/kmanojp/oranslice_rig
PY=./venv/bin/python3
R=experiments/results
S=experiments/scripts
LOG=experiments/logs/m64/full/rebuild.log
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
exec > >(tee -a "$LOG") 2>&1
echo "== rebuild start $(date +%H:%M:%S)"
S30="$(seq -s' ' 900 929)"; S10="$(seq -s' ' 900 909)"; REP="$(seq -s' ' 1000 1009)"
S15="$(seq -s' ' 900 911) 1000 1001 1002"; S30_19="$S15 $(seq -s' ' 912 926)"

# ---- Env B (M64): pre-registered H1-H3
$PY $S/m64_analysis.py --root $R/m64 --out $R/m64/m64_analysis.json

# ---- Env A (M65): three gNBs, replication, sensitivity (AXIOM v2 and MAPPO against the M63 baselines)
$PY $S/m62_analysis.py --root $R/m65_n3_view --seeds $S30 --ref axiom2 \
  --arms axiom2 axiom2_mlp heuristic single_agent_dqn single_agent_dqn_lr1e4 independent_dqn independent_dqn_lr1e4 mappo_tuned \
  --out $R/m65_n3_summary.json
$PY $S/m62_analysis.py --root $R/m65_rep_view --seeds $REP --ref axiom2 \
  --arms axiom2 heuristic single_agent_dqn independent_dqn mappo_tuned --out $R/m65_rep_summary.json
for c in load102 load107 weights; do
  $PY $S/m62_analysis.py --root $R/m65_${c}_view --seeds $S10 --ref axiom2 \
    --arms axiom2 heuristic single_agent_dqn independent_dqn --out $R/m65_${c}_summary.json
done

# ---- Env A federated (v2)
$PY - <<'EOF'
import json, glob
for root, seeds in (("experiments/results/m65_m3", list(range(900, 910))),):
    res = {}
    for f in sorted(glob.glob(f"{root}/fl_gat_ctde_sigma*_results.json")):
        res[f.rsplit("sigma", 1)[1].replace("_results.json", "")] = json.load(open(f))
    json.dump({"seeds": seeds, "noise_multipliers": [float(k) for k in sorted(res, key=float)], "results": res},
              open(f"{root}/campaign_results.json", "w"), indent=1)
    print("m65 m3 campaign file:", sorted(res, key=float))
EOF
$PY $S/m62_analysis.py --root $R/m65_m3_view --seeds $S10 --ref axiom \
  --arms axiom fl_sigma0.0 fl_sigma0.5 fl_sigma1.0 fl_sigma2.0 fl_sigma4.0 --out $R/m65_m3_summary.json
$PY $S/m62_dp_epsilon.py --m3-dir $R/m65_m3 --out $R/m65_m3_epsilon.json
$PY $S/m62_analysis.py --root $R/m65_fedprox_view --seeds 900 901 902 --ref fedavg \
  --arms fedavg fedprox_mu0.01 fedprox_mu0.1 fedprox_mu1.0 --out $R/m65_fedprox_summary.json
$PY $S/m62_analysis.py --root $R/m65_m3_rep_view --seeds $REP --ref axiom --arms axiom fl_sigma0.0 \
  --out $R/m65_m3_replication_summary.json

# ---- Env A disruption (v2 checkpoints, baselines unchanged)
$PY $S/m62_m4_analysis.py --m4-dir $R/m65_m4 --m2-dir $R/m65_m2_view --m3-dir $R/m65_m3 --out $R/m65_m4/m4_summary.json
$PY $S/m62_m4_analysis.py --m4-dir $R/m65_m4_replication --m2-dir $R/m65_m2_rep_view --m3-dir $R/m65_m3_replication \
  --out $R/m65_m4_replication/m4_summary.json

# ---- Env A scaling: N=7 (15 seeds) and N=19 (30 seeds), AXIOM v2 against all three baselines
$PY $S/m63_scaling_tests.py --root $R/m65_scaling --sizes 7 --seeds $S15 \
  --arms axiom2 single_agent_dqn independent_dqn mappo_tuned --out $R/m65_scaling/scaling_tests_n7.json
$PY $S/m63_scaling_tests.py --root $R/m65_scaling --sizes 19 --seeds $S30_19 \
  --arms axiom2 single_agent_dqn independent_dqn mappo_tuned --out $R/m65_scaling/scaling_tests_n19.json
$PY - <<'EOF'
import sys, json, numpy as np
sys.path.insert(0, "experiments/scripts")
from m62_analysis import eval_log, seed_metrics, boot_ci
from scipy.stats import wilcoxon
S = range(900, 912)
g = {s: seed_metrics(p) for s in S if (p := eval_log("experiments/results/m65_scaling/n19_ring", "axiom2", s))}
m = {s: seed_metrics(p) for s in S if (p := eval_log("experiments/results/m65_scaling_mlp/n19_ring", "axiom2_mlp", s))}
c = sorted(set(g) & set(m)); out = {"n": len(c)}
for name, f in (("reward", lambda r: r["reward"]), ("prio_sla", lambda r: 0.5 * (r["sla"]["urllc"] + r["sla"]["embb"]))):
    a = np.array([f(g[s]) for s in c]); b = np.array([f(m[s]) for s in c]); d = a - b
    out[name] = {"gat": float(a.mean()), "mlp": float(b.mean()), "diff": float(d.mean()), "ci": boot_ci(d),
                 "gat_better": int((d > 0).sum()), "ties": int((d == 0).sum()), "mlp_better": int((d < 0).sum()),
                 "p": float(wilcoxon(d).pvalue) if np.any(d != 0) else 1.0}
out["collapsed"] = {"gat": sum(g[s]["collapsed"] for s in c), "mlp": sum(m[s]["collapsed"] for s in c)}
print("Env A N=19 ring attention ablation (v2)", json.dumps(out))
json.dump(out, open("experiments/results/m65_scaling_mlp/n19_ring_ablation.json", "w"), indent=1)
EOF

# ---- validation screens (Env A: both criteria as pre-registered; Env B: collapse criterion primary, addendum 1)
SC=$R/m65_screen; mkdir -p $SC
J=experiments/logs/m64/full/screen_jobs.txt; : > $J
V="../$S/m63_validation_screen.py --backlog-reset"
for arm in axiom2 axiom2_mlp mappo_tuned; do
  echo "$V --env A --cell ../$R/m65_reviewer/base --arm $arm --n 3 --seeds $S30 --out ../$SC/A_n3_base_$arm.json" >> $J; done
for arm in axiom2 mappo_tuned; do
  echo "$V --env A --cell ../$R/m65_reviewer/replication --arm $arm --n 3 --seeds $REP --out ../$SC/A_n3_rep_$arm.json" >> $J; done
for t in fully_connected ring hex; do
  for arm in axiom2 mappo_tuned single_agent_dqn independent_dqn; do
    echo "$V --env A --cell ../$R/m65_scaling/n7_$t --arm $arm --n 7 --topology $t --seeds $S15 --out ../$SC/A_n7_${t}_$arm.json" >> $J
    echo "$V --env A --cell ../$R/m65_scaling/n19_$t --arm $arm --n 19 --topology $t --seeds $S30_19 --out ../$SC/A_n19_${t}_$arm.json" >> $J
  done
  for arm in axiom2 axiom2_mlp mappo_tuned single_agent_dqn independent_dqn; do
    echo "$V --env B --cell ../$R/m64/n7_$t --arm $arm --n 7 --topology $t --seeds $S15 --out ../$SC/B_n7_${t}_$arm.json" >> $J
  done
done
for arm in axiom2 axiom2_mlp mappo_tuned single_agent_dqn independent_dqn; do
  echo "$V --env B --cell ../$R/m64/n3_fully_connected --arm $arm --n 3 --seeds $S30 --out ../$SC/B_n3_$arm.json" >> $J; done
(cd framework && tr '\n' '\0' < ../$J | xargs -0 -P 6 -I{} sh -c '../venv/bin/python3 {} > /dev/null 2>&1')
$PY $S/m63_screen_report.py $(ls $SC/A_*.json) --out $SC/screen_report_envA.json
$PY $S/m63_screen_report.py $(ls $SC/B_*.json) --out $SC/screen_report_envB.json
echo "== rebuild done $(date +%H:%M:%S)"
