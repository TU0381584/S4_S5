#!/bin/bash
# Rebuild every M63 summary, test, screen, and figure from experiments/results/m63_*.
# Run from the repo root after the M63 chain reports "ALL B DONE".
set -u
cd /home/kmanojp/oranslice_rig
PY=./venv/bin/python3
R=experiments/results
S=experiments/scripts
P=experiments/plots
F=Papers_4-5/Paper_5/WPC/figures
LOG=experiments/logs/m63/full/rebuild.log
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
exec > >(tee -a "$LOG") 2>&1
echo "== rebuild start $(date +%H:%M:%S)"

# --- 1. three-gNB campaigns
$PY $S/m62_analysis.py --root $R/m63_reviewer/base --seeds $(seq 900 929) \
  --arms axiom axiom_mlp heuristic single_agent_dqn single_agent_dqn_lr1e4 independent_dqn independent_dqn_lr1e4 \
  --out $R/m63_reviewer/base_summary.json
for c in load102 load107 weights; do
  $PY $S/m62_analysis.py --root $R/m63_reviewer/$c --seeds $(seq 900 909) \
    --arms axiom heuristic single_agent_dqn independent_dqn --out $R/m63_reviewer/${c}_summary.json
done
$PY $S/m62_analysis.py --root $R/m63_reviewer/replication --seeds $(seq 1000 1009) \
  --arms axiom heuristic single_agent_dqn independent_dqn --out $R/m63_reviewer/replication_summary.json
# axiom vs mlp as its own pair (reference = axiom)
$PY $S/m62_analysis.py --root $R/m63_reviewer/base --seeds $(seq 900 929) --arms axiom axiom_mlp \
  --out $R/m63_reviewer/base_mlp_pair.json
# accept-all and shed-mMTC check on the corrected simulator
(cd framework && ../$PY ../$S/m63_acceptall_probe.py --out ../$R/m63_reviewer/accept_all --seeds $(seq -s" " 900 929) --backlog-reset 2>&1 | grep tau=)

# --- 2. federated campaigns (views + merged campaign file)
mkdir -p $R/m63_m3_view
ln -sfn ../m63_reviewer/base/axiom $R/m63_m3_view/axiom
for s in 0.0 0.5 1.0 2.0 4.0; do ln -sfn ../m63_m3/fl_gat_ctde_sigma$s $R/m63_m3_view/fl_sigma$s; done
$PY - <<'EOF'
import json, glob
res = {}
for f in sorted(glob.glob("experiments/results/m63_m3/fl_gat_ctde_sigma*_results.json")):
    sig = f.rsplit("sigma", 1)[1].replace("_results.json", "")
    res[sig] = json.load(open(f))
json.dump({"seeds": list(range(900, 910)), "noise_multipliers": [float(k) for k in sorted(res, key=float)],
           "results": res}, open("experiments/results/m63_m3/campaign_results.json", "w"), indent=1)
print("m3 campaign file:", sorted(res, key=float))
EOF
$PY $S/m62_analysis.py --root $R/m63_m3_view --seeds $(seq 900 909) \
  --arms axiom fl_sigma0.0 fl_sigma0.5 fl_sigma1.0 fl_sigma2.0 fl_sigma4.0 --out $R/m63_m3_summary.json
$PY $S/m62_dp_epsilon.py --m3-dir $R/m63_m3 --out $R/m63_m3_epsilon.json
$PY $S/m62_analysis.py --root $R/m63_fedprox_view --seeds 900 901 902 \
  --arms fedavg fedprox_mu0.01 fedprox_mu0.1 fedprox_mu1.0 --ref fedavg --out $R/m63_fedprox_summary.json
mkdir -p $R/m63_m3_rep_view
ln -sfn ../m63_reviewer/replication/axiom $R/m63_m3_rep_view/axiom
ln -sfn ../m63_m3_replication/fl_gat_ctde_sigma0.0 $R/m63_m3_rep_view/fl_sigma0.0
$PY $S/m62_analysis.py --root $R/m63_m3_rep_view --seeds $(seq 1000 1009) --arms axiom fl_sigma0.0 \
  --out $R/m63_m3_replication_summary.json

# --- 3. disruption
$PY $S/m62_m4_analysis.py --m4-dir $R/m63_m4 --m2-dir $R/m63_m2_view --m3-dir $R/m63_m3 --out $R/m63_m4/m4_summary.json
$PY $S/m62_m4_analysis.py --m4-dir $R/m63_m4_replication --m2-dir $R/m63_m2_rep_view --m3-dir $R/m63_m3_replication \
  --out $R/m63_m4_replication/m4_summary.json

# --- 4. scaling and the attention ablation
$PY $S/m63_scaling_tests.py --root $R/m63_scaling --out $R/m63_scaling/scaling_tests.json
$PY - <<'EOF'
import sys, json, numpy as np
sys.path.insert(0, "experiments/scripts")
from m62_analysis import eval_log, seed_metrics, boot_ci
from scipy.stats import wilcoxon
S = range(900, 912)
g = {s: seed_metrics(p) for s in S if (p := eval_log("experiments/results/m63_scaling/n19_ring", "gat_ctde", s))}
m = {s: seed_metrics(p) for s in S if (p := eval_log("experiments/results/m63_scaling_mlp/n19_ring", "gat_ctde", s))}
c = sorted(set(g) & set(m)); out = {"n": len(c)}
for name, f in (("reward", lambda r: r["reward"]), ("prio_sla", lambda r: 0.5 * (r["sla"]["urllc"] + r["sla"]["embb"]))):
    a = np.array([f(g[s]) for s in c]); b = np.array([f(m[s]) for s in c]); d = a - b
    out[name] = {"gat": float(a.mean()), "mlp": float(b.mean()), "diff": float(d.mean()), "ci": boot_ci(d),
                 "gat_better": int((d > 0).sum()), "ties": int((d == 0).sum()), "mlp_better": int((d < 0).sum()),
                 "p": float(wilcoxon(d).pvalue) if np.any(d != 0) else 1.0}
out["collapsed"] = {"gat": sum(g[s]["collapsed"] for s in c), "mlp": sum(m[s]["collapsed"] for s in c)}
print("N=19 ring attention ablation", json.dumps(out))
json.dump(out, open("experiments/results/m63_scaling_mlp/n19_ring_ablation.json", "w"), indent=1)
EOF

# --- 5. pre-registered validation screen on every learned checkpoint
SC=$R/m63_screen; mkdir -p $SC
J=experiments/logs/m63/full/screen_jobs.txt; : > $J
V="../$S/m63_validation_screen.py --backlog-reset"
for arm in axiom axiom_mlp single_agent_dqn single_agent_dqn_lr1e4 independent_dqn independent_dqn_lr1e4; do
  echo "$V --cell ../$R/m63_reviewer/base --arm $arm --n 3 --seeds $(seq -s' ' 900 929) --out ../$SC/n3_base_$arm.json" >> $J; done
for arm in axiom single_agent_dqn independent_dqn; do
  echo "$V --cell ../$R/m63_reviewer/replication --arm $arm --n 3 --seeds $(seq -s' ' 1000 1009) --out ../$SC/n3_rep_$arm.json" >> $J; done
for n in 7 19; do for t in fully_connected ring hex; do for arm in gat_ctde single_agent_dqn independent_dqn; do
  echo "$V --cell ../$R/m63_scaling/n${n}_$t --arm $arm --n $n --topology $t --seeds $(seq -s' ' 900 911) 1000 1001 1002 --out ../$SC/n${n}_${t}_$arm.json" >> $J; done; done; done
echo "$V --mlp --cell ../$R/m63_scaling_mlp/n19_ring --arm gat_ctde --n 19 --topology ring --seeds $(seq -s' ' 900 911) --out ../$SC/n19_ring_mlp.json" >> $J
(cd framework && tr '\n' '\0' < ../$J | xargs -0 -P 5 -I{} sh -c '../venv/bin/python3 {} > /dev/null 2>&1')
$PY $S/m63_screen_report.py $SC/*.json --out $SC/screen_report.json

# --- 6. figures (superiority and capability figures need numbers copied in by hand afterwards)
$PY $P/paper5_fig3_m2_campaign.py --results $R/m63_m2_view/campaign_results.json --campaign-dir $R/m63_m2_view --out $F/fig3_m2_results
$PY $P/paper5_fig4_m3_privacy.py --m3-results $R/m63_m3/campaign_results.json --m3-campaign-dir $R/m63_m3 \
  --m2-results $R/m63_m2_view/campaign_results.json --m2-campaign-dir $R/m63_m2_view --out $F/fig4_m3_privacy
$PY $P/paper5_fig5_m4_disruption.py --level --m4-results $R/m63_m4/campaign_results.json --m4-campaign-dir $R/m63_m4 \
  --m2-campaign-dir $R/m63_m2_view --m3-campaign-dir $R/m63_m3 --out $F/fig5_m4_disruption
$PY $P/paper5_fig8_scaling_shared.py --root $R/m63_scaling --out $F/fig6_m6_topology
echo "== rebuild done $(date +%H:%M:%S)"
