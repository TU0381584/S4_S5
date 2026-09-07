#!/usr/bin/env bash
# M46-MR2: offline retrain DQN-QoE and DQN-SLA under the MR1 band-aligned
# config (experiments/configs/m46/saclb_m46_train.yaml), matched on
# reward-mode ONLY -- same script, same episode count, same seed set,
# same ClosedLoopKpmSource env for both arms. NO RIG (purely offline).
#
# Seed set (256-261) reuses the SAME 6-seed convention Stage 10/12 already
# established for this exact single-agent DQN offline-training pipeline
# (docs/STAGE10_fullpower_reeval.md section 4: "retrains dqn_sla_v2/
# dqn_qoe_v2 across 5 NEW seeds (257-261)" on top of the original seed256)
# -- not invented for this milestone. Reused here so the resulting
# checkpoints double as the seed pool for the eventual PF2-1 pilot
# ("3-5 seeds" + a replication batch) without a second training pass.
#
# cwd=framework/ + absolute paths for every arg: REQUIRED. This project's
# own run_offline_v2_reverify.sh already documented the failure mode --
# saclb_*.yaml's mapper_checkpoint/iqx paths are relative to framework/,
# not repo root; running from repo root makes every torch.load() fail,
# and without an explicit per-run success check the script can silently
# print COMPLETE after every single training call errored out. This
# script checks for a written checkpoint.pt after every run and aborts
# loudly if one is missing, specifically to not repeat that near-miss.
#
# Uses m46_mr2_train_with_diagnostics.py, not train_offline_live_scale.py
# directly: identical config/env/call path, but non-invasively wraps
# oranslice_drl's DQNPolicy.train_step() (frozen source, unedited -- same
# technique M41 used for send_control()) to also capture the loss/
# grad_norm/epsilon/avg_target_q it already computes and returns on every
# call but that mc_runner.run_mc() never logs anywhere.
set -uo pipefail
ROOT=/home/kmanojp/oranslice_rig
source "$ROOT/venv/bin/activate"
cd "$ROOT/framework"

CONFIG="$ROOT/experiments/configs/m46/saclb_m46_train.yaml"
RESULTS_DIR="$ROOT/experiments/results/m46_mr2/offline_train"
TRAIN="$ROOT/experiments/scripts/m46_mr2_train_with_diagnostics.py"
LOG_DIR="$ROOT/experiments/logs"
EPISODES=300
SEEDS=(256 257 258 259 260 261)

mkdir -p "$LOG_DIR" "$RESULTS_DIR"

echo "=== $(date +%H:%M:%S) M46-MR2 OFFLINE TRAIN START ==="
fail=0
for mode in qoe sla; do
  for seed in "${SEEDS[@]}"; do
    echo "=== $(date +%H:%M:%S) train dqn/$mode seed=$seed ==="
    python3 "$TRAIN" \
      --algorithm dqn --reward-mode "$mode" --config "$CONFIG" \
      --episodes "$EPISODES" --seed "$seed" --results-dir "$RESULTS_DIR" \
      2>&1 | tee -a "$LOG_DIR/m46_mr2_train.log"

    ckpt="$RESULTS_DIR/$mode/seed${seed}/dqn/offline_closed_loop/rep_0/checkpoint.pt"
    diag="$RESULTS_DIR/$mode/seed${seed}/dqn/offline_closed_loop/rep_0/train_diagnostics.jsonl"
    if [[ ! -f "$ckpt" ]]; then
      echo "!!! MISSING checkpoint after run: mode=$mode seed=$seed expected=$ckpt !!!"
      fail=1
    fi
    if [[ ! -f "$diag" ]]; then
      echo "!!! MISSING train_diagnostics after run: mode=$mode seed=$seed expected=$diag !!!"
      fail=1
    fi
  done
done

if [[ $fail -ne 0 ]]; then
  echo "=== $(date +%H:%M:%S) M46-MR2 OFFLINE TRAIN FAILED -- one or more checkpoints missing, see above ==="
  exit 1
fi
echo "=== $(date +%H:%M:%S) M46-MR2 OFFLINE TRAIN COMPLETE -- 12/12 checkpoints written ==="
