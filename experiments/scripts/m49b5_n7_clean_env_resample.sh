#!/usr/bin/env bash
# M49b-5: the one genuine re-run gap M27 itself flagged as missing --
# a properly-powered (12-seed) N=7 resample under the CLEAN,
# unmodified ClosedLoopKpmSource path (m6_run_experiment.py invoked
# directly, no m27_scaling_reframe.py monkeypatch), primary sample
# (900-911, matching M6/M27's own primary seed identity for direct
# comparability) then an independent replication batch (1000-1011,
# extending M6's own 1000-1002 replication-range convention to full
# 12-seed power), same train/eval budget M27 itself used (100/20,
# m6_run_experiment.py's own defaults). Sequential, not parallel --
# both are real CPU training campaigns competing for the same budget
# (established project practice, see docs/PAPER5_REPRODUCIBILITY.md).
set -uo pipefail
cd "$(dirname "$0")/../../framework"
PY=../venv/bin/python3
SCRIPT=../experiments/scripts/m6_run_experiment.py
OUT_ROOT=../experiments/results/m49b_5
CONFIG=qoe_oran_framework/configs/saclb_offline_dqn_n7.yaml
PRIMARY_SEEDS="900 901 902 903 904 905 906 907 908 909 910 911"
REPLICATION_SEEDS="1000 1001 1002 1003 1004 1005 1006 1007 1008 1009 1010 1011"

t0=$(date +%s)
for topology in fully_connected ring hex; do
  tag="n7_${topology}_primary"
  echo "=== [m49b5] $tag (seeds 900-911, ClosedLoopKpmSource, unmodified m6_run_experiment.py) ==="
  $PY $SCRIPT \
    --config-path "$CONFIG" --topology "$topology" \
    --seeds $PRIMARY_SEEDS --train-episodes 100 --eval-episodes 20 \
    --out-dir "$OUT_ROOT/$tag" \
    --arms gat_ctde independent_dqn single_agent_dqn \
    --resume-seeds
  echo "=== [m49b5] $tag done, elapsed so far: $(( $(date +%s) - t0 ))s ==="
done

for topology in fully_connected ring hex; do
  tag="n7_${topology}_replication"
  echo "=== [m49b5] $tag (seeds 1000-1011, independent replication) ==="
  $PY $SCRIPT \
    --config-path "$CONFIG" --topology "$topology" \
    --seeds $REPLICATION_SEEDS --train-episodes 100 --eval-episodes 20 \
    --out-dir "$OUT_ROOT/$tag" \
    --arms gat_ctde independent_dqn single_agent_dqn \
    --resume-seeds
  echo "=== [m49b5] $tag done, elapsed so far: $(( $(date +%s) - t0 ))s ==="
done

echo "=== [m49b5] ALL DONE, total elapsed: $(( $(date +%s) - t0 ))s ==="
