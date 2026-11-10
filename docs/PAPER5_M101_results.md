# M101 results: attention at thirty-seven gNBs, 40 seeds

Pre-registration: docs/PAPER5_M101_preregistration.md (9baec7d8). Analysis: experiments/scripts/m101_analysis.py (086f9b55), unchanged since before any M101 result was read. Output: experiments/results/m101/analysis.json. Launched 2026-11-10 11:26; all 40 jobs exited 0; finished 13:28. Env A, 37 gNBs, hex layout. Two-sided Wilcoxon signed-rank (zero_method wilcox), Holm within each family of two, with 95% bootstrap CIs of the mean paired difference. The manuscript is not changed.

| Test, MLP minus AXIOM | Diff | 95% CI | Median | p | Holm p | W/T/L | Verdict |
|---|---|---|---|---|---|---|---|
| F1 compliance (pp), 20 fresh seeds | +4.20 | [-5.99, 13.73] | 0.00 | 0.65 | 0.85 | 6/10/4 | within chance |
| F1 reward, 20 fresh seeds | +2.61 | [-3.21, 8.48] | 0.00 | 0.42 | 0.85 | 6/9/5 | within chance |
| F2 compliance (pp), 40 pooled | +5.68 | [-0.55, 11.99] | 0.00 | 0.12 | 0.15 | 12/22/6 | within chance |
| F2 reward, 40 pooled | +3.49 | [-0.02, 7.08] | 0.00 | 0.077 | 0.15 | 12/21/7 | within chance |

Per arm, 40 seeds pooled: AXIOM 5 collapsed (Wilson 5.5% to 26.1%), compliance 90.7%, reward 171.8; MLP variant 0 collapsed (0.0% to 8.8%), 96.3%, 175.3.

Judgement against the pre-registered rule: both F2 tests are within chance, so "A per-node MLP encoder ties AXIOM in Env A" stands at thirty-seven gNBs.

Descriptive (not pre-registered): the MLP never collapsed in 40 runs; AXIOM collapsed in 5, each on a seed where the MLP did not (exact McNemar p = 0.0625, not significant). The two encoders give identical results on about half the seeds.
