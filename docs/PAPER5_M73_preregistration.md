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
