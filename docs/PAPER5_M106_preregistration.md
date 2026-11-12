# M106: the two cells where checkpoint selection changes a claim (pre-registration)

Committed on 2026-11-12, after M105's results were read and before any M106 run.

## Why

Checkpoint selection (M67 V1) changes a claim in two places:

1. Env A, 3 gNBs. In M67's development run (seeds 7000 to 7019), AXIOM's reward lead over DQN-SA fell from +0.350 (p 0.036) with last checkpoints to +0.046 (p 0.084) with selected ones. The paper reports AXIOM ahead of DQN-SA there on 120 seeds with last checkpoints. Only 20 development seeds have been run with selection.
2. Env B, 7 gNBs, ring. In M105 (seeds 10000 to 10009), AXIOM against DQN-I moved from within chance with last checkpoints to AXIOM ahead with selected ones, at the smallest Holm p ten seeds allow.

M106 retests both on fresh seeds. Whatever the author decides about adopting selection, the paper's wording at these two cells depends on the answer, and both cells would be part of any full rerun.

## Runs

- Runner experiments/scripts/m104_run.py with M102_VARIANT=gat, exactly as in M105. M67 V1 selection is applied to every arm, each run writes eval/ (selected) and eval_last/ (last), and DQN-SA is seeded.
- Arms: axiom2, single_agent_dqn, independent_dqn.
- Cells and fresh seeds:
  - A_n3: Env A, 3 gNBs, fully connected, the paper's three-gNB setting (m64_run.py --env A --n 3). Seeds 10010 to 10039 (30).
  - B_n7_ring: Env B, 7 gNBs, ring. Seeds 10010 to 10029 (20).
- None of these seeds, nor their evaluation (5000 + seed) or validation (20000 + seed) streams, appears in any earlier launch record or result folder.
- cwd framework/, OMP/MKL/OPENBLAS threads 1, M63_BACKLOG_RESET=1, M64_AXIOM_V2=1, at most 6 jobs at a time. That is 90 + 60 = 150 jobs. Output m106/<cell>/<arm>/seed<seed>.

## Tests (two-sided Wilcoxon signed-rank, zero_method wilcox, paired by seed, fresh seeds only)

- Family S, selected checkpoints: AXIOM minus DQN-SA and AXIOM minus DQN-I, on reward per step and priority-slice compliance, in both cells. That is 8 tests, with Holm over the 8.
- Family L, last checkpoints: the same 8 tests on the same runs, with Holm over the 8.
- Verdicts are AXIOM ahead, baseline ahead (Holm p < 0.05) or within chance. Each test reports the mean, a 95% bootstrap CI (10,000 resamples, default_rng(0)), the median and wins/ties/losses.

## Questions, fixed here

- Q1: with selected checkpoints, is AXIOM ahead of DQN-SA on reward at 3 gNBs (family S)? If it is within chance, the paper's three-gNB claim against DQN-SA does not survive selection.
- Q2: with selected checkpoints, is AXIOM ahead of DQN-I in Env B at 7 gNBs ring, on reward and on compliance (family S)? If so, M105's verdict change replicates.
- Descriptive only:
  - Q1 pooled with M67's 20 development seeds (m67_dev/V1/A3_base). Those seeds informed this question, so the pooled figure is not a confirmation.
  - Q2 pooled with M105's 10 seeds, which have already been read.
  - Selected minus last per arm, with collapse counts.

## Analysis

experiments/scripts/m106_analysis.py, committed with this file and before any M106 run. The manuscript does not change until the author reviews the results.
