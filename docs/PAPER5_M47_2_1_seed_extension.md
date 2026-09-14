# M47-2-1 — extend the checkpoint pool to 12/arm (OFFLINE)

Trains DQN-QoE and DQN-SLA for 6 new seeds (262-267), extending MR2's
existing 6-seed pool (256-261) to 12/arm -- clears the >=11/arm
very-conservative power bar M47-1's power calculation established.
Identical setup to MR2 in every respect except the seed value: same
`experiments/configs/m46/saclb_m46_train.yaml`, same
`ClosedLoopKpmSource`, same `m46_mr2_train_with_diagnostics.py`
entrypoint, same 300-episode budget, same hyperparameters (all baked
into `build_policy()`'s construction, untouched here) -- differing
ONLY in `--reward-mode` (qoe/sla) and `--seed`, matching this
milestone's own standing constraint exactly.

## Disk

Before: 21G available (86% used). Pruned 6 superseded gate-phase-only
gNB logs from PF2-1a's own bring-up cycles (467M, never referenced by
any analysis -- same category MR4's cleanup already established as
safe) before starting. After pruning: 22G available. After training
(offline, no live-rig logs generated): 21G available -- the 12 new
checkpoints/diagnostics/omega-logs together are small (matching MR2's
own ~537M footprint for its 12; this training run added a comparable
amount).

## (1) Seed independence, confirmed before any training time was spent

`experiments/scripts/m47_2_1_seed_independence_check.py`: constructs
the EXACT seeded objects this project's own training entrypoint uses
(`ClosedLoopKpmSource(seed=seed, ...)` via the same
`kpm_source_factory` pattern `m46_mr2_train_with_diagnostics.py`
itself uses, plus `RANEnv(..., seed=seed)`), draws a 20-step
deterministic (all-accept) trajectory from each of the 12 seeds
(256-267, existing + new together), and hashes the full per-step
observation (pending-request slice/gNB assignments, per-slice
`prb_used_ratio`/`queue_len_norm`) into a fingerprint.

**Result: all 12 seeds produce distinct fingerprints, zero
collisions** -- confirmed empirically, not assumed from consecutive-
integer seeding. Full fingerprints in the script's own stderr output
(`experiments/logs/m47_2_1_console.log` does not include this --
the check was run separately before training; re-run the script
directly to reproduce).

## (2) Full in-band action-range exercise -- the pass criterion, 12/12

Reused `m46_mr2_convergence_check.py` unmodified
(`experiments/scripts/m47_2_1_convergence_check.py`, overriding only
`SEEDS`/`OUT_DIR` so this run's `convergence_report.csv` doesn't
overwrite MR2's own already-committed one for seeds 256-261) -- same
criterion MR2's 12 original runs were judged against, applied to these
12 new ones:

| mode | seed | urllc values | embb values | full range? |
|---|---|---|---|---|
| qoe | 262 | 6,7,8 | 5,6,7,8,9,10 | yes |
| qoe | 263 | 6,7,8 | 5,6,7,8,9,10 | yes |
| qoe | 264 | 6,7,8 | 5,6,7,8,9,10 | yes |
| qoe | 265 | 6,7,8 | 5,6,7,8,9,10 | yes |
| qoe | 266 | 6,7,8 | 5,6,7,8,9,10 | yes |
| qoe | 267 | 6,7,8 | 5,6,7,8,9,10 | yes |
| sla | 262 | 6,7,8 | 5,6,7,8,9,10 | yes |
| sla | 263 | 6,7,8 | 5,6,7,8,9,10 | yes |
| sla | 264 | 6,7,8 | 5,6,7,8,9,10 | yes |
| sla | 265 | 6,7,8 | 5,6,7,8,9,10 | yes |
| sla | 266 | 6,7,8 | 5,6,7,8,9,10 | yes |
| sla | 267 | 6,7,8 | 5,6,7,8,9,10 | yes |

**12/12 exact match to `EXPECTED_RANGE` (urllc {6,7,8}, embb
{5,6,7,8,9,10}), zero exceptions -- identical result to MR2's own
original 12/12.** mmtc's fixed point (5) also confirmed unchanged in
every run (not tabulated above, matches by construction since
`ceiling_step_ratio` doesn't apply to mmtc's zero-width band).

## (3) Convergence signature -- consistent with MR2, expected, not a problem

Per this milestone's own explicit instruction: this section is
reported, not interpreted as any verdict on the checkpoints'
usefulness (Stage 3->10 precedent). Final epsilon = 0.0500 in all 12
runs (the documented analytic floor, confirms the frozen decay
schedule ran as intended, same as MR2). Reward: mostly flat-to-
declining Q1->Q4 (10/12 negative delta, matching MR2's own
"reward does NOT improve... in ANY of the 12 runs" finding almost
exactly -- 2 SLA seeds here, 264 and 266/267, show small positive
Q1->Q4 deltas, a degree of seed-to-seed variation MR2's own report
already flagged as real, not an aggregation artifact). Loss: grows in
11/12 runs (matching MR2's own finding and explanation -- TD loss
tracks bootstrapped-target magnitude/variance, not an accuracy metric
that must fall, and this congested action space produces larger,
noisier returns as training proceeds). **This is the expected MR2
signature, reproduced -- not investigated further, per this
milestone's own standing instruction not to alter config/env/reward
to "fix" convergence (which would reintroduce the always-serve
degeneracy P0/Stage5 already found and moved past).**

## (4) Checkpoint paths + provenance

All 12 new checkpoints land in the SAME directory tree MR2's original
6 already occupy (`experiments/results/m46_mr2/offline_train/{mode}/seed{N}/dqn/offline_closed_loop/rep_0/`)
-- not a separate `m47` tree -- so `m46_mr3_live_revalidate.py`'s
existing `checkpoint_path()` finds them unmodified for M47-2-2's live
trust-gating, no script changes needed there. Full paths + config/env/
seed/hyperparameter provenance: `experiments/results/m47_2_1/manifest.csv`
(also includes `experiments/results/m47_2_1/convergence_report.csv`
for the full per-seed reward/loss curve data).

Provenance, identical across all 12: `experiments/configs/m46/saclb_m46_train.yaml`
(MR1's corrected config, unedited), `ClosedLoopKpmSource`,
`algorithm=dqn`, `episodes=300`, `--reward-mode` in `{qoe, sla}`
(the only intentional axis of variation besides seed), all other
hyperparameters identical to MR2 by construction (same entrypoint
script, no arguments changed beyond `--seed`/`--reward-mode`).

## GATE M47-2-1

**(1) Seed independence**: confirmed, 12/12 distinct, no collisions.
**(2) Full in-band action-range exercise**: 12/12, exact match, the
pass criterion is met with zero exceptions. **(3) Convergence
signature**: consistent with MR2, reported as expected per this
milestone's own instruction, not flagged as a problem. **(4)
Provenance**: `experiments/results/m47_2_1/manifest.csv` +
`convergence_report.csv`.

## STOP

Pool now stands at 12/arm (6 original + 6 new), all 12 new checkpoints
pass the only criterion this gate checks. Per this milestone's own
gating, awaiting go before M47-2-2 (live trust-gating the 12 new
checkpoints against the MR3c protocol -- offline convergence predicts
nothing about live behavior, Stage 12's own established finding, so
none of these checkpoints enters the powered pool without passing that
gate too).
