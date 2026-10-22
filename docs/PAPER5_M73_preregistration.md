# M73: scaling past nineteen gNBs (pre-registration)

Committed on 2026-10-22, before any M73 run. The scaling study stops at nineteen gNBs. M73 extends it to thirty-seven, the three-ring hex cluster, the next standard cellular cluster size after 7 and 19. Every check is reported whether it holds or fails, and nothing here replaces a result already reported. Output goes to experiments/results/m73/.

## Setup

- Environment: Env A, the static-load shared-budget simulator, as in the reported scaling campaign.
- Config: experiments/configs/saclb_offline_dqn_n37.yaml, built from the N=19 config exactly as N=7 and N=19 were built from N=3. Only the gNB list (37 gNBs of 100 PRBs), synthetic_arrivals_per_step (37, one arrival per gNB per step) and max_pending_per_step (148, the same 4x headroom) differ. Every slice, reward and episode parameter is unchanged.
- Runner: experiments/scripts/m73_run.py, a wrapper around m64_run.py. The frozen framework defines the hex layout for 7 and 19 cells only. The wrapper extends hex_cluster_coords to 37 cells with the framework's own ring walk (rings 0 to 3), and `m73_run.py --check` confirms that it reproduces the 7- and 19-cell layouts exactly and gives the 90 edges of a three-ring hex grid. The single-agent DQN's initialisation is seeded as in m66c_seeded_single.py. Neither the framework nor m64_run.py is modified.
- Hyperparameters: unchanged from N=19 for every arm. No tuning at N=37. A timing pilot on seed 2000 with 10 training episodes was run only to size the campaign, and its results are not used.
- Arms: AXIOM v2 (axiom2), single-agent DQN (seeded), independent DQN, MAPPO with the setting used in the reported scaling campaign (mappo_tuned), and the static rule that sheds every mMTC request (rule_static), for reference in the text.
- Layouts: AXIOM is the only arm whose computation depends on the layout. In Env A the simulator, the three baselines and the static rule never read the adjacency, as the identical independent-DQN results across layouts at N=7 and N=19 confirm. The baselines and the rule are therefore run once per seed, in the hex cell, and paired with AXIOM under each layout.
- Seeds: hex 900-926 and 1000-1002 (30 seeds, as at N=19). Ring and fully-connected, AXIOM only, 900-911 and 1000-1002 (15 seeds, as at N=7). Evaluation is on the held-out stream 5000 + seed, as before.
- Order: the hex cell on seeds 900-911 and 1000-1002 runs first for every arm, then the remaining hex seeds, then the ring and fully-connected AXIOM runs, then the reported-only MAPPO variant below.

## Predictions

Tests are paired Wilcoxon signed-rank tests on per-seed reward per step and on priority-slice compliance (the mean of URLLC and eMBB SLA compliance), as in the scaling campaign.

- P1, primary, hex, 30 seeds. AXIOM beats the single-agent DQN, the independent DQN and MAPPO on priority-slice compliance and on reward. Holm over these 6 tests, each adjusted p < 0.05 with AXIOM ahead.
- P2, ring and fully-connected, 15 seeds each. The same 6 comparisons under each layout, Holm over the 12 tests, each adjusted p < 0.05 with AXIOM ahead.
- P3. AXIOM's priority-slice compliance pooled over the three layouts is at least 90%.
- P4. AXIOM collapses into accepting every request in at most 10% of its N=37 runs, using the collapse flag of the existing analysis.

## Reported only

- AXIOM's lead over the best baseline on pooled priority-slice compliance at 37 gNBs, next to the 32.0 points at 19.
- The static rule's priority-slice compliance at 37 gNBs.
- Collapse counts, training time per seed and parameters at execution for every arm.
- MAPPO with the configuration the M70 grid selected for Env A (actor LR 1e-3, 4 epochs, minibatch 256, 900 training episodes, three times every other arm's budget) against AXIOM on hex seeds 900-911 and 1000-1002, if time allows.

## Results (campaign 04:16 to 12:36 on 2026-10-22; analysis in experiments/results/m73/analysis.json)

All 167 jobs exited cleanly. 4 of 4 predictions hold; 8 rows were reported only.

- **P1 holds.** On the 30 hex seeds AXIOM beats the single-agent DQN, the independent DQN and MAPPO by 34.9, 61.5 and 36.9 points of priority-slice compliance and by 29.5, 25.9 and 29.0 reward per step, winning 26 to 29 of 30 seeds, all at Holm p ≤ 1.1e-5.
- **P2 holds.** Under the ring and fully-connected layouts the leads are 32.0 to 67.8 points and 18.3 to 27.5 reward per step, all 12 at Holm p ≤ 0.0061.
- **P3 holds.** Pooled AXIOM compliance is 93.69% [89.79, 97.16] over 60 runs (URLLC 96.7%, eMBB 90.7%), down from 97.3% at 19 gNBs.
- **P4 holds at the bound.** AXIOM collapses in 6 of 60 runs (hex 918, 919, 924; ring 901, 1001; fully-connected 902), against 1 of 90 at 19 gNBs. Collapsed runs keep 59% to 65%; the others average 96.9% to 98.1% per layout.
- Reported: baselines keep 58.7% (single-agent DQN, 26 of 30 collapsed), 56.7% (MAPPO) and 32.1% (independent DQN); the lead over the best baseline is 35.0 points (32.0 at 19). The static rule keeps 99.98%. The grid-selected MAPPO (900 episodes) keeps 65.6% on 15 hex seeds; AXIOM beats it by 29.2 points (13/15, p 0.00085) and 23.23 reward per step (15/15, p 6.1e-5).
- Load check: 1.151 to 1.152 pending requests per gNB per step, as at 3, 7 and 19 gNBs; the pending cap binds in 1 of 3,000 steps.
- Complexity at 37 gNBs (complexity_n37.json, idle machine): AXIOM 7,782 parameters and 9.89 ms per step. Re-running m64_complexity.py reproduced the stored 3/7/19 latencies within 5%. The single-agent DQN latency, absent from m64/complexity.json, was measured with the same workload at all four sizes (0.61/1.42/3.95/8.02 ms), and the manuscript's earlier 0.55/1.30/3.58, which no committed script produces, was replaced by it.
