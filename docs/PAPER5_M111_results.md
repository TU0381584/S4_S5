# M111: second seed extension of the Env A scaling cells (results)

Results for docs/PAPER5_M111_preregistration.md (committed 8f45623e, 2026-11-17 01:08:41 before any run). The analysis is experiments/results/m111/analysis.json, produced by m111_analysis.py as committed.

## Runs

All 536 of 536 jobs exited 0 (experiments/logs/m111/done.txt, 01:08 to 13:19 on 2026-11-17). Fresh seeds 14000 to 14014 in every Env A cell; evaluation streams 19000 to 19014. "Current" below is the paper's sample (stored seeds pooled with the M107 seeds), "new" is the 15 new seeds alone, "pooled" is both.

## Scaling cells (7, 19 and 37 gNBs): nothing changes

All 54 comparisons of AXIOM with a learned baseline (three sizes, three layouts, three baselines, reward and compliance) are AXIOM ahead under Holm p < 0.05 on the current sample, on the new seeds alone, and pooled. No verdict changes and no verdict fails to replicate. Pooled leads over the closest baseline stay at the paper's values: 17.6 to 28.5 compliance points at 7 gNBs (smallest: ring, DQN-SA, +13.7), 31.3 to 40.1 at 19 and 33.1 to 62.5 at 37. Pooled samples are 45, 75 and 75 runs (30 for the 37-gNB ring and fully connected layouts).

## Env A, three gNBs (Table 3 and its text): three verdicts change

| Comparison (AXIOM minus) | Current (n=60) | New seeds (n=15) | Pooled (n=75) |
|---|---|---|---|
| DQN-SA, reward | +0.312 ahead | -0.095 within chance | +0.230 ahead |
| DQN-SA, compliance | +1.929 ahead | -1.313 within chance | +1.281 within chance (verdict changes) |
| DQN-I, reward | +1.061 ahead | +0.745 within chance | +0.998 ahead |
| DQN-I, compliance | +5.026 ahead | +3.688 within chance | +4.758 ahead |
| MAPPO, reward | +2.482 ahead | +2.382 ahead | +2.462 ahead |
| MAPPO, compliance | +19.276 ahead | +17.054 within chance | +18.832 ahead |
| MLP encoder, reward | +0.068 ahead | -0.035 within chance | +0.048 within chance (verdict changes) |
| MLP encoder, compliance | -0.137 within chance | -0.840 within chance | -0.278 within chance |
| Static rule, reward | -0.101 within chance | -0.288 within chance | -0.138 static rule ahead (verdict changes) |
| Static rule, compliance | -0.954 static rule ahead | -2.447 within chance | -1.253 static rule ahead |

The new-seed column has 15 pairs, so a within-chance verdict there is weak evidence, but several leads (over DQN-SA and MLP encoder) change sign on the new seeds alone. Holm families are those of M107.

## What follows

Per the pre-registration the manuscript changes only after the author has seen this. Still to do once the author agrees: pool the new seeds into every Env A number, Fig. 5, Table 3, the per-gNB table and the verifier checks, re-evaluate the new checkpoints per gNB with m110_pergnb.py (about 2 CPU-hours), recompute the 5-point rule, and disclose the second extension in Section 5 and Online Resource 1.
