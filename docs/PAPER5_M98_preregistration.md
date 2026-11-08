# M98: confirmation tests on the paper's weaker findings (pre-registration)

Committed on 2026-11-09, before any M98 run whose result is reported. The author asked for more confirmation tests on the weaker findings. Four findings rest on margins near the significance threshold or on a pre-registered check that failed; each is re-tested on fresh seeds never used before (A to C) or by pooling stored runs that no earlier analysis combined (D). Every result is reported whether it holds or fails. Nothing here changes the manuscript, which changes only after the author reviews the results. Output: experiments/results/m98/. Analysis: experiments/scripts/m98_analysis.py, written after this commit and before any M98 result is read. The framework and the runners are not modified.

## Feasibility (checked before this commit, not results)

- Fresh seeds 9500 to 9539, 9600 to 9629 and 9700 to 9719 appear in no launch record (logs/*/jobs.txt) and no result folder.
- The pooled sources of A2, C2 and D read with m66_verify's reader: m66d_fresh/D1_A_n3 (40 seeds, AXIOM and DQN-SA), m66_fresh/B_n7_ring and m67_confirm_envB/B_n7_ring (10 + 10 seeds, AXIOM and the MLP variant), m76/b1_shift_n19 and m96/C_fresh_shift/n19_hex (15 + 15 seeds, AXIOM, the static rule and the carried tuned rule at each load). These were opened only to count seeds; no difference between policies was computed.
- Median training times from stored runs: AXIOM 593 s (Env A, 3 gNBs), 579 s (Env B, 3), 791 s (Env B, 7 ring); MLP variant 712 s; DQN-SA 53 to 85 s; DQN-I 181 s; MAPPO 73 s. About 25 CPU-hours in all.

## Runs (cwd framework/, OMP_NUM_THREADS=MKL_NUM_THREADS=OPENBLAS_NUM_THREADS=1, M63_BACKLOG_RESET=1, M64_AXIOM_V2=1, at most 5 jobs at a time)

- A, Env A, 3 gNBs, fresh seeds 9500 to 9539: m64_run.py --arm axiom2 --env A --n 3; m66c_seeded_single.py --arm single_agent_dqn --env A --n 3. Output m98/A_n3.
- B, Env B, 3 gNBs fully connected, fresh seeds 9600 to 9629: m64_run.py with --arm axiom2, mappo_tuned, independent_dqn, rule_local (tuned on these seeds' training streams over the usual grid); m66c_seeded_single.py --arm single_agent_dqn. Then m96_shift.py on the stored checkpoints at nominal, 110%, 115% and 120% load, arms axiom2 mappo_tuned single_agent_dqn independent_dqn rule_local. Output m98/B_n3 and m98/B_shift/n3.
- C, Env B, 7 gNBs ring, fresh seeds 9700 to 9719: m64_run.py --arm axiom2 and --arm axiom2_mlp --n 7 --topology ring. Output m98/C_n7_ring.
- D, no new runs.

Every learned arm trains for 300 episodes and is evaluated for 50 episodes on the held-out stream 5000 + seed, as in every reported campaign.

## Criteria (two-sided Wilcoxon signed-rank, zero_method wilcox; reward per step; Holm within each family)

- A1. AXIOM against the seeded DQN-SA on the 40 fresh seeds. Reported: Env A, 3 gNBs, 0.311 at p = 0.066 (30 seeds); earlier fresh seeds +0.159 at p = 0.09 (40 seeds). HOLDS if the mean paired difference is positive at p < 0.05.
- A2. The same on the 80 fresh seeds of A and M66d (4000 to 4039) pooled. HOLDS if positive at p < 0.05.
- B1. The failed check R-B1 at 3 gNBs repeated: AXIOM earns more reward per step than each of MAPPO, DQN-SA and DQN-I at 110%, 115% and 120% load, 9 tests, Holm. HOLDS if all 9 are positive at Holm-adjusted p < 0.05.
- B2. AXIOM against the tuned local rule at 110%, 115% and 120% load, 3 tests, Holm. HOLDS if all 3 are positive at Holm-adjusted p < 0.05 (the paper reports 21 to 23 wins of 25 at Holm p <= 0.0002 at 3 gNBs).
- B3, reported. The nominal-load comparison with the tuned rule, where the paper has the rule ahead.
- C1. The MLP variant against AXIOM, Env B, 7 gNBs ring, on the 20 fresh seeds. Reported: H3 missed significance after Holm (+1.12, p = 0.061); 10 fresh ring seeds gave +1.38 at p = 0.006. HOLDS (MLP ahead) if the mean of MLP minus AXIOM is positive at p < 0.05.
- C2. The same on all 40 fresh ring seeds (C, m66_fresh 3000 to 3009, M67 8100 to 8109) pooled. HOLDS if positive at p < 0.05.
- D1. The static rule against AXIOM, Env B, 19 gNBs, at 110%, 115% and 120% load, on the 30 seeds of M76 (reported) and M96 c (fresh) pooled, 3 tests, Holm. The paper says the static rule's lead of 1.8 to 2.0 stays within chance at Holm p >= 0.08 (15 seeds). HOLDS (static rule ahead) if all 3 are positive at Holm-adjusted p < 0.05; otherwise the paper's "within chance" stands.
- Reported for every block: 95% bootstrap CIs (10,000 resamples, default_rng(0)), wins/ties/losses, and collapsed runs.

## What changes if a criterion fails or holds

Nothing automatically. The results and a proposed wording are reported to the author, who decides what enters the paper.
