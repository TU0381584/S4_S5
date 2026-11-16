# M111: second seed extension of the Env A scaling cells (pre-registration)

Committed before any M111 run.

## Why

The author asked for more runs per policy in the main paper's scaling figure (Env A, 3 to 37 gNBs, one dot per run) and chose 15 new seeds per cell, pooled into every estimate. This is the second extension of these cells decided after their results had been seen, the first being M107. It is also decided after M110 showed that AXIOM's per-gNB lead is small. The paper must disclose both facts. No stopping rule depends on the outcome: all 15 seeds per cell are run, all are pooled, and no further extension of these cells follows from this one's results.

## Runs

New seeds, never used before: 14000 to 14014, with evaluation streams 19000 to 19014. Each arm runs exactly as in M107 and in the campaign that produced its stored runs: experiments/scripts/m107_run.py (m64_run.py, or m73_run.py at 37 gNBs), cwd framework/, one thread, M63_BACKLOG_RESET=1 and M64_AXIOM_V2=1, 300 training and 50 evaluation episodes, last checkpoint.

| Cell | Sample it extends | Arms |
|---|---|---|
| Env A, 3 gNBs | m65_n3_view with its M107 seeds, 60 runs | axiom2, axiom2_mlp, single_agent_dqn, independent_dqn, mappo_tuned, rule_static |
| Env A, 7 gNBs, three layouts | 30 runs per layout | axiom2, single_agent_dqn, independent_dqn, mappo_tuned, rule_static |
| Env A, 19 gNBs, three layouts | 60 runs per layout | the same |
| Env A, 37 gNBs, hex | 60 runs | the same |
| Env A, 37 gNBs, ring and fully connected | 30 runs each | axiom2 |
| Env A, accept-all at 7, 19, 37 gNBs, hex | as in M107 | rule_accept_all |

That is 525 training runs and 11 rule evaluations (536 jobs, experiments/logs/m111/jobs.txt), about 70 CPU-hours and about 12 hours at six parallel jobs. Output goes to experiments/results/m111/. Env B is not extended.

After the runs, experiments/scripts/m110_pergnb.py re-evaluates the new checkpoints of the four learned policies with the per-gNB recorder, under the same exactness rule as M110.

## Analysis

experiments/scripts/m111_analysis.py, committed with this file, computes each family three ways: on the paper's current sample (stored seeds pooled with the M107 seeds), on the new seeds alone, and on all pooled. The families are those of M107 for Env A: Table 3 at 3 gNBs (AXIOM against each learned baseline, the MLP encoder and the static rule) and the scaling families at 7, 19 and 37 gNBs (AXIOM against each learned baseline under every layout), each on reward and on priority-slice compliance. Tests are two-sided Wilcoxon signed-rank with ties within 1e-9 dropped, Holm within each family, with 95 % bootstrap CIs, wins, ties, losses and collapse counts.

Fixed here:

1. The manuscript reports the pooled values for these cells. Every number, figure, table and verifier check that reads them moves to the pooled sample, including the per-gNB table and the outcome of M110's 5-point rule, which is recomputed on the pooled runs and reported whatever it shows.
2. The new seeds alone form a replication and are reported on their own in Online Resource 1. A verdict that the new seeds alone do not reproduce is reported, whatever the pooled result.
3. If a pooled verdict differs from the current one, the text follows the pooled verdict and says what changed.
4. The confirmation seeds 12000 to 12029 stay unpooled, as their own pre-registration fixed.
5. Campaigns that pair their own runs seed by seed with these cells keep their stored comparisons, as decided for M107.

The manuscript changes only after the pooled results have been read and reported to the author.
