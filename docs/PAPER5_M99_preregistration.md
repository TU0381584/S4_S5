# M99: further confirmation tests (pre-registration)

Committed on 2026-11-10, before any M99 run. The author asked for more confirmation tests to strengthen the paper's findings. Four findings still rest on one sample of 15 to 30 seeds, on a near-miss p value, or on a mean whose CI includes zero. Each is re-tested on fresh seeds never used before (A to C) or by pooling stored runs that no earlier analysis combined (D). Every result is reported whether it holds or fails, and nothing here changes the manuscript, which changes only after the author reviews the results. Output: experiments/results/m99/. Analysis: experiments/scripts/m99_analysis.py, written after this commit and before any M99 result is read. The framework and the runners are not modified.

## Feasibility (checked before this commit, not results)

- Fresh seeds 9800 to 9819, 9840 to 9859 and 9900 to 9939 appear in no launch record (logs/*/jobs*.txt, logs/*/phase*.txt) and no result folder.
- Pooled sources, opened only to count seeds: m70/R4_sharedhead/A_n19_ring (15 seeds), m64/n7_hex and m67_confirm_envB/B_n7_hex (15 + 10 seeds, AXIOM and the MLP variant), m96/B_shift/n3 at 110%, 115% and 120% (25 seeds, AXIOM, MAPPO, DQN-SA, DQN-I), m98/B_shift/n3 (30 seeds), m98/A_n3 and m66d_fresh/D1_A_n3 (40 + 40 seeds). No difference between policies was computed.
- Median training times from stored runs: AXIOM 892 s (Env A, 19 gNBs, ring), 593 s (Env A, 3), 791 s (Env B, 7); MLP variant 712 s; DQN-SA 53 to 85 s. About 26 CPU-hours in all.

## Runs (cwd framework/, OMP_NUM_THREADS=MKL_NUM_THREADS=OPENBLAS_NUM_THREADS=1, M63_BACKLOG_RESET=1, M64_AXIOM_V2=1, at most 5 jobs at a time, longest first)

- A, Env A, 19 gNBs, ring, fresh seeds 9800 to 9819: m64_run.py --arm axiom2 --env A --n 19 --topology ring, as M65 ran AXIOM; and M70_VARIANT=sharedhead m70_run.py --arm axiom2 --env A --n 19 --topology ring, as M70 ran the shared-head variant. Output m99/A_n19_ring and m99/A_sharedhead_n19_ring.
- B, Env A, 3 gNBs, fresh seeds 9900 to 9939: m64_run.py --arm axiom2 --env A --n 3; m66c_seeded_single.py --arm single_agent_dqn --env A --n 3, as in M98 A. Output m99/B_A_n3.
- C, Env B, 7 gNBs, hex, fresh seeds 9840 to 9859: m64_run.py --arm axiom2 and --arm axiom2_mlp --n 7 --topology hex, as in M64 and M67. Output m99/C_n7_hex.
- D, no new runs.

Every learned arm trains for 300 episodes and is evaluated for 50 episodes on the held-out stream 5000 + seed, as in every reported campaign.

## Criteria (two-sided Wilcoxon signed-rank, zero_method wilcox, paired by seed; Holm within each family)

- A1. Per-slice heads at scale. Reported (M70, 15 seeds): the shared-head variant collapses in 9 of 15 seeds and keeps 65.9% priority-slice compliance against AXIOM's 96.8%, losing every seed at Holm p < 0.001. On the 20 fresh seeds, family of two tests (priority-slice compliance, reward per step), AXIOM minus shared head. HOLDS if both are positive at Holm-adjusted p < 0.05. Reported beside it: collapsed runs of each arm with Wilson 95% intervals, and wins.
- B1. AXIOM against the seeded DQN-SA, Env A, 3 gNBs, 40 fresh seeds, reward per step. HOLDS if positive at p < 0.05.
- B2. The same on 120 fresh seeds pooled (B, M98 A 9500 to 9539, M66d 4000 to 4039). HOLDS if positive at p < 0.05 and the 95% bootstrap CI of the mean paired difference excludes zero. The CI condition is added because on 80 seeds the rank test held while that CI included zero.
- C1. The MLP variant against AXIOM, Env B, 7 gNBs, hex, 20 fresh seeds, reward per step, MLP minus AXIOM. Reported: H3 on hex +0.95 at p = 0.095 (15 seeds). HOLDS if positive at p < 0.05.
- C2. The same on 30 fresh hex seeds pooled (C and M67 8100 to 8109). HOLDS if positive at p < 0.05.
- D1. AXIOM against MAPPO, DQN-SA and DQN-I at 110%, 115% and 120% load, Env B, 3 gNBs, on the 55 seeds of M96 (905 to 929) and M98 (9600 to 9629) pooled, reward per step, 9 tests, Holm. Reported per test, with the verdict for each: AXIOM ahead (positive, Holm p < 0.05), behind (negative, Holm p < 0.05), or within chance. No single pass rule; the paper's current sentence (AXIOM leads all three only at 110% load, and from 115% DQN-SA and DQN-I come within 0.21) is judged against these nine verdicts.
- Reported for every block: 95% bootstrap CIs (10,000 resamples, default_rng(0)), wins/ties/losses, medians, and collapsed runs.

## What changes if a criterion fails or holds

Nothing automatically. The results and a proposed wording are reported to the author, who decides what enters the paper.
