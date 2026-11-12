# M107: seed extension of the cells in Figs. 5 and 7 (pre-registration)

Committed on 2026-11-12, before any M107 run.

## Why

The author asked for more runs per policy in Fig. 5 (Env A, 3 to 37 gNBs) and Fig. 7 (Env B, 3 gNBs), and chose to pool new seeds into the plotted samples. Every number the paper reports for these cells is then recomputed on the pooled seeds. The fresh-seed replications (M66, M66d, M80, M96, M98, M99, M101) stay separate and keep their role as independent samples, so no seed already used anywhere is added to a main sample.

## Runs

New seeds, never used before: E30 = 11000 to 11029, and E15 = 11000 to 11014 where a cell has 15 seeds per layout. Their evaluation streams are 16000 to 16029. Each arm runs exactly as in the campaign that produced its stored runs: experiments/scripts/m107_run.py, which is m64_run.py (or m73_run.py at 37 gNBs), cwd framework/, OMP/MKL/OPENBLAS threads 1, M63_BACKLOG_RESET=1 and M64_AXIOM_V2=1. The single-agent DQN is seeded only at 37 gNBs, as in M73. Elsewhere it is unseeded, as in M64 and M65.

| Cell | Stored sample it extends | Arms | New seeds |
|---|---|---|---|
| Env A, 3 gNBs | m65_n3_view, 30 seeds | axiom2, axiom2_mlp, single_agent_dqn, independent_dqn, mappo_tuned, rule_static | E30 |
| Env B, 3 gNBs | m64/n3_fully_connected, 30 seeds | the same, plus rule_accept_all, rule_local, rule_neighbour | E30 |
| Env A, 7 gNBs, fully connected, ring, hex | m65_scaling/n7_*, m70/R1/A_n7_*, 15 seeds each | axiom2, single_agent_dqn, independent_dqn, mappo_tuned, rule_static | E15 |
| Env A, 19 gNBs, three layouts | m65_scaling/n19_*, m70/R1/A_n19_*, 30 seeds each | the same | E30 |
| Env A, 37 gNBs, hex | m73/A_n37_hex, 30 seeds | the same | E30 |
| Env A, 37 gNBs, ring and fully connected | m73/A_n37_ring and _fully_connected, 15 seeds | axiom2 | E15 |
| Env A, accept-all at 7, 19, 37 gNBs (hex) | m75/B_acceptall/n7, n19, n37 | rule_accept_all | E15 at 7, E30 at 19 and 37 |

- The tuned rules in Env B at 3 gNBs are not re-tuned. Each applies the rule its original campaign selected on training streams (m64/n3_fully_connected/rule_local_selection.json and rule_neighbour_selection.json), so the pooled seeds share one tuned rule.
- At 3 gNBs in Env A the static rule is rule_static. The verifier already shows it is identical to the stored "heuristic" runs on all 30 seeds.
- Every training run uses the last checkpoint, as every reported campaign does.
- Jobs run one seed each, at most 6 at a time, longest cells first. Output goes to experiments/results/m107/<cell>/<arm>/seed<seed>.

## Analysis

experiments/scripts/m107_analysis.py, committed with this file and before any run, computes each headline family three ways: on the stored seeds, on the new seeds alone, and pooled. The families are:

- Table 3, Env A at 3 gNBs: AXIOM against every learned baseline and the static rule, on reward and priority-slice compliance.
- H1 and Table 5, Env B at 3 gNBs: AXIOM against every other arm, on both measures.
- The scaling families at 7, 19 and 37 gNBs: AXIOM against each learned baseline, under every layout, on both measures.

The tests are two-sided Wilcoxon signed-rank (ties within 1e-9), with Holm within each family as in the paper, plus 95% bootstrap CIs, wins/ties/losses and collapse counts.

Fixed here:

1. The manuscript reports the pooled values for these cells. Each changed number, figure and table is regenerated from the pooled seeds, and every verifier check that reads these cells moves to the pooled seed lists.
2. The new seeds alone form a replication. A headline verdict that the new seeds alone do not reproduce (AXIOM ahead under Holm p < 0.05 where the stored sample had it ahead) is reported, whatever the pooled result.
3. If a pooled verdict differs from the stored one, the text follows the pooled verdict and says what changed.

The manuscript changes only after the pooled results are read and reported to the author.
