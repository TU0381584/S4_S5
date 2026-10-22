# M74: fresh-seed replication at thirty-seven gNBs (pre-registration)

Committed on 2026-10-22, before any M74 run and after the M73 results (8579e94). M73 found AXIOM's lead growing at 37 gNBs on the seeds of the scaling campaign. M74 retrains every arm on fresh seeds to test whether that holds on seeds never used before. Every check is reported whether it holds or fails, and nothing here replaces a reported result. Output goes to experiments/results/m74/.

## Setup

- Everything as in M73 (docs/PAPER5_M73_preregistration.md): Env A, the N=37 config, experiments/scripts/m73_run.py, unchanged hyperparameters, the hex layout, and the single-agent DQN's initialisation seeded.
- Arms: AXIOM v2 (axiom2), single-agent DQN, independent DQN, MAPPO with the scaling campaign's setting (mappo_tuned), and the static rule (rule_static) for reference in the text.
- Seeds: 6100-6119 (20 seeds), evaluated on streams 11100-11119. No result directory in experiments/results uses any of these seeds, and none of them, as a training or evaluation stream, coincides with a stream used before.
- Only the hex layout is run. M73 found no layout effect at 37 gNBs larger than 1.3 points of compliance.

## Predictions

Paired Wilcoxon signed-rank tests on per-seed priority-slice compliance and reward per step, as in M73.

- F1. AXIOM beats the single-agent DQN, the independent DQN and MAPPO on priority-slice compliance and on reward. Holm over these 6 tests, each adjusted p < 0.05 with AXIOM ahead.
- F2. AXIOM's mean priority-slice compliance is at least 90%.
- F3. AXIOM collapses into accepting every request in at most 2 of 20 seeds (10%).

## Reported only

- AXIOM's lead over the best baseline, next to the 35.0 points of M73.
- Each arm's URLLC and eMBB compliance, reward and collapse count, and the static rule's compliance.
- Pooled over M73's 30 hex seeds and these 20, AXIOM's compliance and collapse rate.

## Results (campaign 13:15 to 18:33 on 2026-10-22; analysis in experiments/results/m74/analysis.json)

All 81 jobs exited cleanly. 3 of 3 predictions hold; 7 rows were reported only.

- **F1 holds.** AXIOM beats the single-agent DQN, the independent DQN and MAPPO by 37.7, 61.0 and 36.5 points of priority-slice compliance and by 35.46, 25.62 and 30.63 reward per step, winning 18 to 19 of 20 seeds in every comparison, all at Holm p ≤ 0.0004.
- **F2 holds.** AXIOM keeps 95.09% [89.38, 99.97] (URLLC 95.4%, eMBB 94.7%).
- **F3 holds.** AXIOM collapses in 1 of 20 seeds (6110).
- Reported: MAPPO 58.5%, single-agent DQN 57.4% (18 of 20 collapsed), independent DQN 34.1% (2 of 20); lead over the best baseline 36.5 points (35.0 in M73). Static rule 99.97%. Pooled with M73's 30 hex seeds, AXIOM keeps 94.2% over 50 seeds and collapses in 4.
