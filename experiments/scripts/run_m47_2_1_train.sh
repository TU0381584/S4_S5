#!/usr/bin/env bash
# M47-2-1: extends the DQN-QoE/DQN-SLA checkpoint pool from MR2's
# original 6 seeds (256-261) to 12 (adding 262-267), for the >=11/arm
# very-conservative power bar the PF2-1 pre-registration needs. This
# is a byte-identical mirror of run_m46_mr2_train.sh (M46-MR2) --
# same config, same episode budget, same env, same script, same
# per-run existence check -- with ONLY the seed set changed. Does NOT
# re-run seeds 256-261 (already trained, already extensively
# live-trust-gated by MR3/MR3c/PF2-1a -- re-running them would waste
# time and risks overwriting checkpoints multiple already-committed
# reports depend on).
#
# Seed independence confirmed first (experiments/scripts/
# m47_2_1_seed_independence_check.py): all 12 seeds 256-267 produce
# distinct 20-step trajectory fingerprints, no collisions -- not
# assumed from consecutive-integer seeding alone.
#
# Checkpoints land in the SAME experiments/results/m46_mr2/offline_train/
# tree MR2's own 6 seeds already occupy (not a separate m47 directory)
# so m46_mr3_live_revalidate.py's existing checkpoint_path() finds them
# unmodified for M47-2-2's live trust-gating -- no script changes
# needed there.
set -uo pipefail
ROOT=/home/kmanojp/oranslice_rig
source "$ROOT/venv/bin/activate"
cd "$ROOT/framework"

CONFIG="$ROOT/experiments/configs/m46/saclb_m46_train.yaml"
RESULTS_DIR="$ROOT/experiments/results/m46_mr2/offline_train"
TRAIN="$ROOT/experiments/scripts/m46_mr2_train_with_diagnostics.py"
LOG_DIR="$ROOT/experiments/logs"
EPISODES=300
SEEDS=(262 263 264 265 266 267)

mkdir -p "$LOG_DIR" "$RESULTS_DIR"

echo "=== $(date +%H:%M:%S) M47-2-1 OFFLINE TRAIN START (seeds 262-267, extending MR2's pool) ==="
fail=0
for mode in qoe sla; do
  for seed in "${SEEDS[@]}"; do
    echo "=== $(date +%H:%M:%S) train dqn/$mode seed=$seed ==="
    python3 "$TRAIN" \
      --algorithm dqn --reward-mode "$mode" --config "$CONFIG" \
      --episodes "$EPISODES" --seed "$seed" --results-dir "$RESULTS_DIR" \
      2>&1 | tee -a "$LOG_DIR/m47_2_1_train.log"

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
  echo "=== $(date +%H:%M:%S) M47-2-1 OFFLINE TRAIN FAILED -- one or more checkpoints missing, see above ==="
  exit 1
fi
echo "=== $(date +%H:%M:%S) M47-2-1 OFFLINE TRAIN COMPLETE -- 12/12 new checkpoints written (6 seeds x 2 arms) ==="
