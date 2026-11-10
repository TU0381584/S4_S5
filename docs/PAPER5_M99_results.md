# M99 results: further confirmation tests

Pre-registration: docs/PAPER5_M99_preregistration.md (1584a86e). Analysis: experiments/scripts/m99_analysis.py (9bb7a88c), unchanged since before any M99 result was read. Output: experiments/results/m99/analysis.json. Launched 2026-11-10 05:08; all 124 jobs exited 0; finished 09:42. Two-sided Wilcoxon signed-rank (zero_method wilcox), paired by seed, with the 95% bootstrap CI of the mean paired difference (10,000 resamples, default_rng(0)). W/T/L counts the first-named policy's wins. The manuscript is not changed.

## Verdicts

| ID | Criterion | Verdict |
|---|---|---|
| A1 | AXIOM ahead of the shared-head variant on compliance and reward, Env A, 19 gNBs, ring, 20 fresh seeds, Holm | HOLDS |
| B1 | AXIOM beats the seeded DQN-SA, Env A, 3 gNBs, 40 fresh seeds | HOLDS |
| B2 | The same on 120 fresh seeds pooled, with the CI of the mean above zero | HOLDS |
| C1 | MLP variant ahead of AXIOM, Env B, 7 gNBs, hex, 20 fresh seeds | HOLDS |
| C2 | The same on 30 fresh hex seeds pooled | HOLDS |
| D1 | AXIOM against MAPPO, DQN-SA and DQN-I past the tuning load, Env B, 3 gNBs, 55 seeds pooled (reported per test) | see below |

## Numbers

| Test | Diff | 95% CI | Median | p | Holm p | W/T/L | Collapsed (first/second) |
|---|---|---|---|---|---|---|---|
| A1 compliance (pp), AXIOM - shared head | +28.40 | [21.64, 34.52] | +34.08 | 0.00013 | 0.00026 | 19/1/0 | 1/15 |
| A1 reward, AXIOM - shared head | +9.298 | [7.166, 11.247] | +11.709 | 0.00013 | 0.00026 | 19/1/0 | 1/15 |
| B1 AXIOM - DQN-SA, 40 fresh | +0.511 | [0.154, 0.932] | +0.016 | 0.0027 | | 24/9/7 | 0/0 |
| B2 AXIOM - DQN-SA, 120 pooled | +0.267 | [0.082, 0.469] | +0.012 | 4.9e-5 | | 71/28/21 | 1/0 |
| C1 MLP - AXIOM, 20 fresh hex | +1.700 | [0.923, 2.411] | +2.132 | 0.00071 | | 16/0/4 | 0/0 |
| C2 MLP - AXIOM, 30 pooled hex | +1.394 | [0.642, 2.071] | +1.977 | 0.0010 | | 23/0/7 | 0/0 |
| D1 AXIOM - MAPPO 110% | +1.304 | [0.994, 1.644] | +1.179 | 8.2e-9 | 7.4e-8 | 47/0/8 | 0/0 |
| D1 AXIOM - MAPPO 115% | +0.802 | [0.516, 1.131] | +0.767 | 9.9e-7 | 7.9e-6 | 43/0/12 | 0/0 |
| D1 AXIOM - MAPPO 120% | +0.531 | [0.215, 0.903] | +0.314 | 0.0032 | 0.016 | 38/0/17 | 0/0 |
| D1 AXIOM - DQN-SA 110% | +0.517 | [0.267, 0.776] | +0.491 | 0.00091 | 0.0054 | 37/0/18 | 0/0 |
| D1 AXIOM - DQN-SA 115% | +0.098 | [-0.097, 0.293] | +0.037 | 0.61 | 0.61 | 28/0/27 | 0/0 |
| D1 AXIOM - DQN-SA 120% | -0.200 | [-0.390, -0.009] | -0.329 | 0.028 | 0.11 | 22/0/33 | 0/0 |
| D1 AXIOM - DQN-I 110% | +0.565 | [0.339, 0.790] | +0.581 | 3.8e-5 | 0.00026 | 40/0/15 | 0/0 |
| D1 AXIOM - DQN-I 115% | +0.137 | [-0.033, 0.309] | +0.037 | 0.18 | 0.52 | 29/0/26 | 0/0 |
| D1 AXIOM - DQN-I 120% | -0.093 | [-0.249, 0.064] | -0.136 | 0.19 | 0.52 | 22/0/33 | 0/0 |

Block A collapse counts with Wilson 95% intervals: AXIOM 1 of 20 (0.9% to 23.6%), priority-slice compliance 95.4%; shared head 15 of 20 (53.1% to 88.8%), 67.0%.

D1 verdicts at Holm p < 0.05: AXIOM ahead of MAPPO at 110%, 115% and 120%; ahead of DQN-SA and DQN-I at 110%; within chance against DQN-SA and DQN-I at 115% and 120%.

## Checks added after the pre-registered analysis (descriptive, not pre-registered)

- Sign-flip permutation test of the mean paired difference (200,000 draws, default_rng(0)): B1 p = 0.011, B2 p = 0.0072, C1 p = 0.0008. The mean-based test agrees with the rank test, unlike M98 A, where the CI of the mean included zero.
- Every fresh-seed comparison of the MLP encoder with AXIOM in Env B at seven gNBs (M98 C ring 20, M66 ring 10, M67 ring 10, M99 hex 20, M67 hex 10; 70 seeds): MLP minus AXIOM +1.133 reward per step, 54 wins and 14 losses, permutation p < 0.0001.
- Block B: the median paired difference is small (+0.012) and 28 of 120 seeds tie exactly, so AXIOM's lead over DQN-SA at three gNBs in Env A is consistent across seeds but small on most of them.
