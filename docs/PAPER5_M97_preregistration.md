# M97: the tuned local rule in Env A at 37 gNBs (pre-registration)

Committed on 2026-11-07, before any M97 run whose result is reported. The capability figure (fig_capability, Fig. 10) left the tuned rule's two Env A cells at 37 gNBs, priority-slice compliance and URLLC backlog delay, marked "not tested", because the tuned local rule was only ever run in Env B. This campaign measures them. The result is reported whatever it is. Output: experiments/results/m97/. The framework and the runners are not modified.

## Feasibility (checked before this commit, not results)

One 2-episode training-stream run of a local rule (tau_q 0.2, tau_e 0.2) in Env A at 37 gNBs on the hex layout, seed 900, ran in 0.3 s through m64_run.rule_eval with m73_run's 37-cell layout. Its output went to a scratch folder and is not used.

## Procedure

- Cell: Env A, 37 gNBs, hex layout, the same cell and seeds as the reported 37-gNB baselines (m73/A_n37_hex). Seeds 900 to 926 and 1000 to 1002, 30 in all.
- Tuning exactly as every reported tuned rule: m73_run.py --arm rule_local --env A --n 37 --topology hex, unchanged. Each of the 95 rules of the local grid in m64_run.RULE_GRID runs 10 episodes on each seed's training stream, the rule with the highest mean training-stream reward is kept, and it is evaluated for 50 episodes on each seed's held-out stream 5000 + seed. Output: experiments/results/m97/A_n37_hex.
- Backlog delay with the M77 recorder: m77_kpi.py --env A --n 37 --topology hex --cell m97/A_n37_hex --arm rule_local_cell on the same 30 seeds, each re-evaluation checked against the stored evaluation log. Output: experiments/results/m97/A_n37_hex_kpi.

## What is reported

- Mean priority-slice (URLLC and eMBB) compliance over the 30 held-out evaluations. In the figure the cell is met if it is at least 90%, the threshold every other column uses.
- Mean URLLC backlog delay in control periods. In the figure the cell is met if it is below 0.5, the threshold every other column uses.
- The selected thresholds and their training-stream reward.
- Descriptive comparison with the static rule and AXIOM on the same seeds (mean paired difference in compliance and in reward per step, two-sided Wilcoxon signed-rank, zero_method wilcox). No hypothesis is tested.

## Budget

About 1.3 CPU-hours (28,500 training-stream episodes and 1,500 held-out episodes at about 0.15 s each), plus the recorder pass. One job at a time, OMP_NUM_THREADS=MKL_NUM_THREADS=OPENBLAS_NUM_THREADS=1.
