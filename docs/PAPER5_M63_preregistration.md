# M63 pre-registration: validation screen and rerun analysis

Written and committed on 2026-10-15, after the M63 rerun was launched (14:28) and before any M63 result was read. Its git timestamp is the evidence that this plan was not tuned to the M63 outcomes.

## Why M63 exists

M62 diagnostics found that the shared-budget simulator never cleared queue backlog between episodes. With mMTC shed, only about 0.5 PRB of headroom remains, so a backlog built by one early transient persisted through every later episode of a run. This produced bimodal outcomes for every policy, including the oracle rule in 7 of 30 seeds.

M63 reruns every campaign with `--backlog-reset` (`install_backlog_reset` in `experiments/scripts/m62_reviewer_experiments.py`, or `M63_BACKLOG_RESET=1` for the wrapped runners). The rerun keeps the M62 seeds, arms, conditions, and hyperparameters. All results go to `experiments/results/m63_*`.

## The screen, fixed now

The screen is applied to every trained checkpoint of every learned arm. It runs 5 greedy episodes, with epsilon 0 and no learning, on the checkpoint's own training stream: env seed = training seed, never the 5000+seed evaluation stream. It uses the same simulator settings as training.

A checkpoint FAILS the screen if either holds:
1. it blocks no request in those 5 episodes, or
2. fewer than 90% of its blocks target mMTC.

Both thresholds were chosen from the M62 old-simulator checkpoints, so they are fixed here and must not be changed after M63 results are seen. Implementation: `experiments/scripts/m63_validation_screen.py`, extended to the baseline arms with the identical rule.

## How it will be reported

- Raw results: every seed, screened or not. These remain the primary results.
- Screened results: per arm, the number of seeds that fail, and the metrics over the seeds that pass.
- Two-seed protocol: seeds are paired in ascending order within each cell, and the first passing seed of each pair is deployed. If both fail, the first seed is deployed anyway. Report the mean priority-slice SLA and the number of collapses among deployed policies.
- The screen is scored against evaluation outcomes on these counts:
  - true positives: collapse, or priority-slice SLA below 0.5;
  - false positives;
  - misses.
- The identical screen and protocol are applied to the single-agent and independent DQN baselines. AXIOM gets no screen the baselines do not get.

## Analysis plan, fixed now

- Same metrics, tests, and families as M62:
  - Wilcoxon signed-rank tests, with Holm correction per family;
  - 10,000-resample bootstrap CIs;
  - priority-slice SLA as the mean of URLLC and eMBB compliance.
- The attention claim is dropped from the paper unless the MLP ablation reverses. The paper attributes gains to the shared encoder, per-slice heads, and joint training.
- Every M63 number replaces its M62 counterpart, including any number that gets worse.
