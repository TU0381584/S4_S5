# M98 results: confirmation tests on the weaker findings

Pre-registration: docs/PAPER5_M98_preregistration.md (d800a0a6). Analysis: experiments/scripts/m98_analysis.py (c4a52f5a, 46efd7c6), unchanged since before any M98 result was read. Output: experiments/results/m98/analysis.json. Launched 2026-11-09 04:25, 131 jobs, all exit 0, finished 08:42. Two-sided Wilcoxon signed-rank (zero_method wilcox) on reward per step, paired by seed; 95% bootstrap CI of the mean paired difference (10,000 resamples, default_rng(0)); W/T/L counts the first-named policy's wins. The manuscript is not changed.

## Verdicts

| ID | Criterion | Verdict |
|---|---|---|
| A1 | AXIOM beats DQN-SA, Env A 3 gNBs, 40 fresh seeds | HOLDS |
| A2 | Same, 80 fresh seeds pooled with M66d | HOLDS |
| B1 | AXIOM beats MAPPO, DQN-SA, DQN-I at 110-120% load, Env B 3 gNBs, all 9 at Holm p<0.05 | FAILS |
| B2 | AXIOM beats the tuned rule at 110-120% load, Env B 3 gNBs, all 3 at Holm p<0.05 | HOLDS |
| C1 | MLP variant ahead of AXIOM, Env B 7 ring, 20 fresh seeds | HOLDS |
| C2 | Same, 40 fresh seeds pooled with M66 and M67 | HOLDS |
| D1 | Static rule ahead of AXIOM at 110-120% load, Env B 19 gNBs, 30 seeds pooled, all 3 at Holm p<0.05 | HOLDS |

## Numbers

| Test | Diff | 95% CI | p | Holm p | W/T/L | Collapsed (first/second) |
|---|---|---|---|---|---|---|
| A1 AXIOM - DQN-SA, 40 | +0.131 | [-0.056, 0.331] | 0.014 | | 25/9/6 | 0/0 |
| A2 AXIOM - DQN-SA, 80 | +0.145 | [-0.058, 0.362] | 0.0038 | | 47/19/14 | 1/0 |
| B1 AXIOM - MAPPO 110% | +1.273 | [0.812, 1.776] | 3.2e-6 | 2.9e-5 | 25/0/5 | 0/0 |
| B1 AXIOM - MAPPO 115% | +0.836 | [0.397, 1.379] | 3.1e-4 | 0.0025 | 21/0/9 | 0/0 |
| B1 AXIOM - MAPPO 120% | +0.608 | [0.125, 1.221] | 0.040 | 0.22 | 19/0/11 | 0/0 |
| B1 AXIOM - DQN-SA 110% | +0.485 | [0.121, 0.864] | 0.036 | 0.22 | 20/0/10 | 0/0 |
| B1 AXIOM - DQN-SA 115% | +0.099 | [-0.194, 0.406] | 0.69 | 1 | 16/0/14 | 0/0 |
| B1 AXIOM - DQN-SA 120% | -0.194 | [-0.478, 0.109] | 0.15 | 0.61 | 13/0/17 | 0/0 |
| B1 AXIOM - DQN-I 110% | +0.456 | [0.130, 0.786] | 0.016 | 0.12 | 20/0/10 | 0/0 |
| B1 AXIOM - DQN-I 115% | +0.104 | [-0.131, 0.347] | 0.60 | 1 | 15/0/15 | 0/0 |
| B1 AXIOM - DQN-I 120% | -0.080 | [-0.301, 0.154] | 0.30 | 0.90 | 10/0/20 | 0/0 |
| B2 AXIOM - tuned rule 110% | +0.413 | [0.240, 0.592] | 1.4e-4 | 1.4e-4 | 26/0/4 | 0/0 |
| B2 AXIOM - tuned rule 115% | +0.396 | [0.244, 0.557] | 2.1e-5 | 6.2e-5 | 24/0/6 | 0/0 |
| B2 AXIOM - tuned rule 120% | +0.364 | [0.198, 0.541] | 6.3e-5 | 1.3e-4 | 24/0/6 | 0/0 |
| B3 AXIOM - tuned rule nominal (reported) | -0.626 | [-0.904, -0.388] | 1.2e-6 | | 4/0/26 | 0/0 |
| C1 MLP - AXIOM, 20 | +0.941 | [0.148, 1.592] | 0.0084 | | 16/2/2 | 0/0 |
| C2 MLP - AXIOM, 40 | +0.937 | [0.419, 1.416] | 5.4e-4 | | 31/2/7 | 0/0 |
| D1 static - AXIOM 110% | +1.549 | [0.439, 2.863] | 0.012 | 0.035 | 8/22/0 | 0/2 |
| D1 static - AXIOM 115% | +1.608 | [0.472, 2.974] | 0.018 | 0.036 | 7/23/0 | 0/2 |
| D1 static - AXIOM 120% | +1.645 | [0.474, 3.031] | 0.028 | 0.036 | 6/24/0 | 0/2 |

The tuned rule selected on the B training streams is tau_c 0, tau_e 0.2, the same rule as in the paper.

## Notes read from the per-seed values (descriptive, not pre-registered tests)

- A1: median paired difference +0.029. AXIOM ties DQN-SA exactly on 9 seeds and wins most of the rest by small margins, while three losses of 1.1 to 1.8 reward per step widen the bootstrap CI of the mean to include zero. The rank test and the CI of the mean therefore disagree; the lead is consistent across seeds but small on average.
- D1: on 22 to 24 of the 30 seeds AXIOM earns exactly the static rule's reward (difference 0.0). On the remaining 6 to 8 the static rule leads, by 0.001 to 12.9 reward per step, and AXIOM never leads. Two of those seeds (908, 7006) are AXIOM collapses; without them the mean lead is 1.15 to 1.25. The Wilcoxon test therefore rests on the 6 to 8 non-tied seeds, all in the static rule's favour.
- B1: past the tuning load at three gNBs the lead over MAPPO survives Holm at 110% and 115%, but none of the leads over DQN-SA or DQN-I does, and at 120% both DQNs are ahead on the point estimate, within chance.
