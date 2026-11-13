# M108: confirmation seeds for the M107 verdict changes (pre-registration)

Committed on 2026-11-14, before any M108 run.

## Why

The author asked for more confirmation tests and seeds. When M107 was pooled into the paper, some verdicts changed, and M107's new seeds alone did not reproduce two leads. M108 runs a third, independent sample of 30 seeds for exactly those comparisons. These seeds have never been used, so the sample confirms or fails to confirm each verdict on its own.

## Runs

- **Seeds:** 12000 to 12029 (C30). Evaluation streams are 17000 to 17029 (EVAL_OFFSET 5000).
- **Runner:** every arm runs exactly as in M107, with experiments/scripts/m107_run.py unchanged. The working directory is framework/, OMP/MKL/OPENBLAS threads are 1, and M63_BACKLOG_RESET=1 and M64_AXIOM_V2=1 are set.
- **Tuned rules:** rule_local and rule_neighbour apply the rule their original campaign selected (m64/n3_fully_connected/*_selection.json), not re-tuned.
- **DQN-SA:** unseeded, as in M64, M65 and M107.
- **Checkpoints:** every learned run uses the last checkpoint.
- **Scheduling:** one job per learned seed, at most 6 at a time, longest first.
- **Output:** experiments/results/m108/<cell>, logs in experiments/logs/m108. The job list is logs/m108/jobs.txt, written by m108_analysis.py --jobs: 365 jobs, about 6 hours.

| Cell | Arms | Seeds |
|---|---|---|
| Env A, 3 gNBs | axiom2, axiom2_mlp, single_agent_dqn, independent_dqn, mappo_tuned, rule_static | C30 |
| Env B, 3 gNBs | the same, plus rule_accept_all, rule_local, rule_neighbour | C30 |
| Env A, 7 gNBs, ring | axiom2, single_agent_dqn | C30 |

## Analysis

experiments/scripts/m108_analysis.py was committed with this file. Its code was dry-run on M107's runs before any M108 run, and it reproduced M107's new-seed results.

The tests are two-sided Wilcoxon signed-rank tests (ties within 1e-9), with 95% bootstrap CIs of the paired mean difference. Holm correction is applied within each family and measure:

- **Env A, 3 gNBs:** AXIOM against DQN-SA, DQN-I, MAPPO, the MLP encoder and the static rule. That is 5 tests per measure. The paper's Table 3 family also holds learning-rate variants that M108 does not rerun.
- **Env B, 3 gNBs:** AXIOM against those learners and all four rules, 8 tests per measure.
- **Env A, 7 gNBs, ring:** AXIOM against DQN-SA, 1 test per measure.

### Pre-registered targets

Each target is judged on the M108 seeds alone.

| Target | Setting | Direction to confirm | Measure |
|---|---|---|---|
| T1 | Env A, 3 gNBs | AXIOM ahead of DQN-SA | reward |
| T2 | Env A, 3 gNBs | AXIOM ahead of the MLP encoder | reward |
| T3 | Env A, 3 gNBs | static rule ahead of AXIOM | reward |
| T4 | Env B, 3 gNBs | neighbour rule ahead of AXIOM | reward |
| T5 | Env B, 3 gNBs | AXIOM ahead of the neighbour rule | compliance |
| T6 | Env A, 7 gNBs, ring | AXIOM ahead of DQN-SA | reward |
| T7 | Env A, 7 gNBs, ring | AXIOM ahead of DQN-SA | compliance |

### Outcomes

A target has one of three outcomes:
- **Confirmed:** the M108 seeds alone give the stated direction at Holm p < 0.05.
- **Same direction, within chance.**
- **Opposite direction**, flagged as significant if Holm p < 0.05.

Every target is reported whatever its outcome. The stored, M107 and M108 seeds pooled are also computed, for information only.

### What follows

The manuscript does not change with M108. Its results go to the author, who decides whether to report the confirmation and whether to pool the M108 seeds into the plotted samples.
