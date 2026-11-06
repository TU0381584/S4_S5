# M96: replication and robustness checks for the strengthened claims (pre-registration)

Committed on 2026-11-07, before any M96 run whose result is reported. Three checks target the claims a reviewer is most likely to question, and each is reported whether it holds or fails. Nothing here changes the manuscript, which changes only after the author reviews the results. Output: experiments/results/m96/. Analysis: experiments/scripts/m96_analysis.py, written after this commit and before any M96 result is read. The framework is not modified.

## Feasibility (checked before this commit, not results)

experiments/scripts/m96_shift.py evaluates stored Env B checkpoints of AXIOM, MAPPO, DQN-SA and DQN-I, and the rules, under shifted load, setting the simulator constants exactly as m72_shift.py does. Under nominal conditions it reproduced the stored evaluation exactly (reward, blocks and SLA) for 14 policy and seed pairs. These were AXIOM, MAPPO, DQN-SA, DQN-I and the tuned rule at 7 gNBs ring, MAPPO, DQN-SA and DQN-I at 3 gNBs, MAPPO, DQN-SA, DQN-I and the carried rule at 19 gNBs hex, and AXIOM and the carried rule on the fresh 19-gNB seeds. Seeds 8000 to 8019 were checked to be unused anywhere in the results.

## M96a. Zero-shot transfer on fresh seeds (Env A, hex)

- Train AXIOM and MAPPO (mappo_tuned) at 7 gNBs on the hex layout on fresh seeds 8000 to 8019, exactly as the reported scaling campaign did (m64_run.py, 300 episodes). Also train AXIOM at 19 gNBs (m64_run.py) and at 37 gNBs (m73_run.py) on the same seeds and layout. Evaluate the static rule and accept-all at 19 and 37 gNBs on the same held-out streams.
- Run the 7-gNB checkpoints unchanged at 19 and 37 gNBs with m92_transfer.py, 50 episodes on each seed's held-out stream 5000 + seed.
- R-A1, the abstract's clause. HOLDS if AXIOM transferred from 7 gNBs keeps a mean priority-slice compliance above 93% at both 19 and 37 gNBs.
- R-A2 and R-A3, one family with Holm over 4 tests. AXIOM transferred from 7 gNBs beats accept-all (R-A2) and MAPPO transferred from 7 gNBs (R-A3) on priority-slice compliance at 19 and at 37 gNBs. Each HOLDS with a positive mean paired difference at Holm-adjusted p < 0.05 (two-sided Wilcoxon signed-rank, zero_method wilcox).
- R-A4, descriptive. Transferred minus trained-at-N AXIOM at 19 and 37 gNBs, mean paired difference, bootstrap 95% CI (10,000 resamples, default_rng(0)), and Wilcoxon p.

## M96b. Learned baselines past the tuning load (Env B, stored checkpoints)

- Cells and seeds as in the load-shift results already reported. 3 gNBs fully connected on seeds 905 to 929 (m64/n3_fully_connected), 7 gNBs ring on seeds 900 to 911 and 1000 to 1002 (m64/n7_ring), and 19 gNBs hex on the same seeds (m75/D_envB_n19_hex).
- AXIOM, MAPPO, DQN-SA, DQN-I and the tuned local rule (carried from 7 gNBs at 19), neither retrained nor re-tuned, at 80%, 100%, 105%, 110%, 115% and 120% of the nominal load.
- R-B1, per size. HOLDS if AXIOM earns more reward per step than each of MAPPO, DQN-SA and DQN-I at 110%, 115% and 120% load, every one of the 9 tests at Holm-adjusted p < 0.05 within that size.
- Reported. Every other load, and the learned baselines against the tuned rule.

## M96c. The load-shift lead on fresh seeds (Env B, 19 gNBs hex)

- The 15 fresh-seed checkpoints of the earlier fresh-seed run (m80/D_envB_n19_hex_fresh, seeds 7000 to 7014), the carried tuned rule and the static rule, and the learned baselines, at 100%, 110%, 115% and 120% of the nominal load.
- R-C1. HOLDS if AXIOM earns more reward per step than the carried tuned rule at 110%, 115% and 120% load, all three at Holm-adjusted p < 0.05. This replicates on fresh seeds the margin the abstract states.
- Reported. The nominal comparison, where the reported seeds have the rule ahead, and AXIOM against each learned baseline at every load.

## Budget

About 23 CPU-hours, mostly the 80 Env A training runs (AXIOM at 7, 19 and 37 gNBs and MAPPO at 7, 20 seeds each), with about 3 CPU-hours of evaluation. At most 5 parallel jobs, longest first, OMP_NUM_THREADS=MKL_NUM_THREADS=OPENBLAS_NUM_THREADS=1.
