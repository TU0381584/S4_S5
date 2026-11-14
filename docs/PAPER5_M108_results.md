# M108: confirmation seeds for the M107 verdict changes (results)

These are the results for docs/PAPER5_M108_preregistration.md, which was committed in bb57af09 before any run.

## Runs

The campaign ran from 2026-11-14 06:14 to 11:39. All 365 of 365 jobs exited 0 (experiments/logs/m108/done.txt), and no job log shows an error or a traceback.

- Every comparison has its full sample: 30 paired seeds on the M108 seeds alone, 90 pooled at 3 gNBs and 60 pooled in the 7-gNB ring.
- AXIOM collapsed in none of the runs.
- The rule arms used the selections from their original campaign, copied into each cell (rule_local_selection.json, rule_neighbour_selection.json).

## Analysis

The pre-registered analysis is experiments/results/m108/analysis.json, produced by m108_analysis.py, which was committed and dry-run on M107 before any run. Nothing was changed after the runs.

As pre-registered, the Holm families are M108's own: 5 baselines in Env A, 8 in Env B and 1 in the ring, within each measure. The paper's Table 3 family is larger because it includes learning-rate variants. So the pooled lines below are for information only and are not the numbers the paper would print.

## Pre-registered targets, judged on the M108 seeds alone

| Target | M108 diff (95% CI) | Holm p | Outcome | All seeds pooled (n) |
|---|---|---|---|---|
| T1 Env A 3 gNBs, AXIOM ahead of DQN-SA, reward | +0.521 (+0.245, +0.845) | 0.0040 | confirmed | +0.381, p 1.1e-05 (90) |
| T2 Env A 3 gNBs, AXIOM ahead of MLP encoder, reward | +0.473 (+0.176, +0.854) | 0.0062 | confirmed | +0.203, p 1.8e-04 (90) |
| T3 Env A 3 gNBs, static rule ahead of AXIOM, reward | -0.019 (-0.058, +0.011) | 0.33 | same direction, within chance | -0.074, p 0.023 (90) |
| T4 Env B 3 gNBs, neighbour rule ahead of AXIOM, reward | -0.240 (-0.429, -0.069) | 0.15 | same direction, within chance | -0.237, p 0.0025 (90) |
| T5 Env B 3 gNBs, AXIOM ahead of neighbour rule, compliance | +1.529 (+0.271, +2.689) | 0.077 | same direction, within chance | +1.320, p 0.0014 (90) |
| T6 Env A 7 ring, AXIOM ahead of DQN-SA, reward | +1.939 (+1.256, +2.665) | <1e-4 | confirmed | +2.854, p 2.0e-08 (60) |
| T7 Env A 7 ring, AXIOM ahead of DQN-SA, compliance | +11.778 (+7.613, +16.094) | <1e-4 | confirmed | +13.461, p 9.4e-08 (60) |

Four targets are confirmed and three point the same way but are within chance. No target goes the opposite way.

- T1, T2: the two AXIOM leads that turned significant only after pooling M107 are confirmed by an independent third sample. Both leads are larger here than in either earlier sample.
- T3: the static rule's lead over AXIOM in Env A is small here (-0.019) and not significant. It is significant only when all 90 seeds are pooled.
- T4, T5: in Env B the neighbour rule's reward lead and AXIOM's compliance lead have the same size as in the pooled data, but 30 seeds alone do not reach Holm p < 0.05. For both, the bootstrap CI of the mean excludes zero.
- T6, T7: the 7-gNB ring leads over DQN-SA, which M107's new seeds did not reproduce, are confirmed clearly on the M108 seeds.

## Other comparisons on the M108 seeds alone

- Env A, 3 gNBs: AXIOM is ahead of DQN-I and MAPPO on both measures, and ahead of the MLP encoder on compliance (+3.2, p 0.032).
- Env B, 3 gNBs: AXIOM ties the MLP encoder (reward -0.002, p 0.95; compliance +0.20, p 0.86). AXIOM is ahead of every learner and of the static and accept-all rules. The tuned local rule is ahead of AXIOM on both measures (reward -0.472, compliance -2.90, both p ≤ 1e-4). This matches the paper's finding that tuned rules beat all learners in Env B.

## What follows

The manuscript is unchanged. The author decides whether to report M108 as a confirmation sample and whether to pool its seeds into the plotted samples. The eval logs are kept uncompressed (20 GB). They can be compressed with experiments/scripts/gzip_verified.sh if the author approves.
