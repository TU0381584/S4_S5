# M92: zero-shot cluster-size transfer (pre-registration)

Committed on 2026-11-06, before any transfer evaluation. Gate T of the external review plan. Stored checkpoints trained at seven gNBs are evaluated, unchanged and without any training or tuning, at 19 and 37 gNBs. Every criterion is reported as HOLDS or FAILS, and nothing here replaces a reported result. Runner: experiments/scripts/m92_transfer.py. Analysis: experiments/scripts/m92_analysis.py, written after this commit and before any result is read. Output: experiments/results/m92/. The framework is not modified.

## Feasibility (checked before this commit, no transfer run)

- AXIOM (axiom2) and its MLP variant execute through the shared encoder and the per-slice Q-heads, whose shapes do not depend on the cluster size. The stored network also holds the QMIX mixer, whose input is the flattened joint state (N x 9) and which only the training loss uses. The framework's own load_checkpoint therefore fails at a new size. The runner copies every parameter except mixer.* and refuses any other missing or unexpected key. AXIOM keeps 7,782 execution parameters at 19 and 37 gNBs.
- MAPPO executes through its shared actor, whose input is the acting gNB's own 9 node features plus the 3-way slice one-hot, at any size. Only the actor is loaded; the critic, which reads the joint state, is used only in training.
- DQN-SA and DQN-I cannot transfer. DQN-SA's input and output are sized by the joint state of N gNBs and DQN-I holds one network per gNB. This is a structural fact, not a run.
- No Env A MLP-variant checkpoint exists at seven gNBs (Env A has it only at three gNBs and at nineteen on the ring). The attention question (H-T4) is therefore tested in Env B only, where 15 seven-gNB hex MLP checkpoints exist.
- Harness check, not a result. Six stored checkpoints were evaluated at their own size through the runner (Env A AXIOM at 7, 19 and 37 gNBs hex, Env A MAPPO at 7 hex, Env B MLP at 7 hex, Env B AXIOM at 19 hex, seed 900 each). All six reproduced their stored evaluation logs exactly, and the Env B per-gNB compliance file reproduced M75's exactly.

## Design

- Arms. AXIOM-7 to N, MLP-7 to N (Env B only), MAPPO-7 to N: the seven-gNB checkpoint of each seed, evaluated at N. References, stored and reused unchanged: AXIOM trained at N, the static rule, and accept-all. In Env A neither the rules nor the simulator read the layout (M75 pre-registration, part B), so the hex rule runs serve both layouts.
- Seeds. The 15 seven-gNB seeds, 900-911 and 1000-1002, each evaluated for 50 episodes on its held-out stream 5000 + seed at the target size. This is the same stream on which the stored references for that seed were evaluated, so every comparison is paired by seed. Nothing is tuned.
- Primary cells, Env A hex: sources m65_scaling/n7_hex (axiom2, mappo_tuned). Targets 19 and 37 gNBs hex. References: m65_scaling/n19_hex and m73/A_n37_hex (axiom2), m70/R1/A_n19_hex and m73/A_n37_hex (rule_static), m75/B_acceptall/n19 and n37 (rule_accept_all).
- Secondary cells. Env A ring: sources m65_scaling/n7_ring, targets 19 and 37 ring, references m65_scaling/n19_ring and m73/A_n37_ring (axiom2) and the same rule runs. Env B hex 7 to 19: sources m64/n7_hex (axiom2, axiom2_mlp, mappo_tuned), references m75/D_envB_n19_hex (axiom2, rule_static, rule_accept_all).
- Endpoints. Priority-slice SLA compliance, the mean of URLLC and eMBB compliance (primary). In Env A this is the cluster-level compliance the paper reports there. In Env B at 19 gNBs cluster-level compliance saturates at 16.7% to 24.7% for every learned policy, so the Env B endpoint is the per-gNB compliance of M75 part D, with cluster-level compliance reported alongside. Secondary: reward per gNB per step, and the collapse count (seeds whose evaluation blocks no request).
- Tests. Paired by seed, two-sided Wilcoxon signed-rank test (zero_method wilcox, as everywhere in the paper), Holm correction within each family below. Bootstrap 95% percentile CIs of the mean paired difference, 10,000 resamples, numpy default_rng(0).

## Hypotheses and criteria

Primary family, Env A hex, priority-slice SLA, Holm over these 4 tests:
- H-T1 at 19 and at 37. HOLDS at N if AXIOM-7 to N minus accept-all is positive with Holm-adjusted p < 0.05.
- H-T2 at 19 and at 37. HOLDS at N if the mean of AXIOM-7 to N minus MAPPO-7 to N is at least 0 and AXIOM is not significantly behind (no Holm-adjusted p < 0.05 with a negative mean). Reported in addition: whether AXIOM is significantly ahead.

H-T3, descriptive, no test. AXIOM-7 to N minus AXIOM trained at N on priority-slice SLA and on reward per gNB per step, mean paired difference with its bootstrap CI, at 19 and 37 in every Env A cell and at 19 in Env B.

H-T4, Env B hex 7 to 19, two-sided, one test. AXIOM-7 to 19 against MLP-7 to 19 on per-gNB priority-slice SLA, with reward per gNB per step reported. Reported either way.

Secondary families, the same H-T1 and H-T2 criteria with Holm within each family: Env A ring (4 tests), Env B hex at 19 (2 tests, per-gNB priority-slice SLA).

Reported only: every arm's mean, CI and collapse count per cell; AXIOM-7 to N and MAPPO-7 to N against the static rule; MAPPO-7 to N against accept-all.

## Stop conditions

- T-S1. If AXIOM-7 to 37 has a lower mean priority-slice SLA than accept-all at 37 gNBs (hex, primary; also checked on ring), flag TRANSFER-LIMITATION. The paper reports it in Section 7 only.
- T-S2. If MLP-7 to 19 beats GAT-7 to 19 at p < 0.05 in H-T4, flag it. The text keeps "attention adds nothing", strengthened.
- T-S3. If GAT-7 to 19 beats MLP-7 to 19 at p < 0.05 in H-T4, flag ATTENTION-TRANSFER. Title and claims stay unchanged until the author decides.

## Budget

About 3,000 CPU-seconds of evaluation (14 s per seed at 19 gNBs and 26 s at 37, measured in the harness check): Env A hex and ring, 2 arms x 15 seeds x 2 sizes each, and Env B hex, 3 arms x 15 seeds. At most 5 jobs in parallel, OMP_NUM_THREADS=MKL_NUM_THREADS=OPENBLAS_NUM_THREADS=1, M75_PERGNB=1.
