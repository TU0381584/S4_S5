# M100 results: the two ablations at thirty-seven gNBs

Pre-registration: docs/PAPER5_M100_preregistration.md (58fb2f55). Analysis: experiments/scripts/m100_analysis.py (e913192f), unchanged since before any M100 result was read. Output: experiments/results/m100/analysis.json. Launched 2026-11-10 09:45; all 40 jobs exited 0; finished 11:24. Env A, 37 gNBs, hex layout, seeds 8000 to 8019, with AXIOM read from m96/A_fresh/n37_hex. Two-sided Wilcoxon signed-rank (zero_method wilcox), Holm within each family of two, with 95% bootstrap CIs of the mean paired difference. The manuscript is not changed.

| Test | Diff | 95% CI | Median | p | Holm p | W/T/L |
|---|---|---|---|---|---|---|
| E1 AXIOM - shared head, compliance (pp) | +31.67 | [23.24, 39.80] | +37.93 | 0.00028 | 0.00039 | 17/2/1 |
| E1 AXIOM - shared head, reward | +17.19 | [12.83, 21.43] | +21.28 | 0.00020 | 0.00039 | 18/2/0 |
| E2 MLP - AXIOM, compliance (pp) | +7.16 | [0.04, 14.92] | 0.00 | 0.069 | 0.14 | 6/12/2 |
| E2 MLP - AXIOM, reward | +4.37 | [0.52, 8.43] | 0.00 | 0.069 | 0.14 | 6/12/2 |

Per arm (20 seeds each): AXIOM 2 collapsed (Wilson 2.8% to 30.1%), compliance 91.1%, reward 172.3; MLP variant 0 collapsed (0.0% to 16.1%), 98.3%, 176.7; shared head 18 collapsed (69.9% to 97.2%), 59.4%, 155.1.

Verdicts: E1 HOLDS. E2: within chance on both measures.

Descriptive (not pre-registered): the two encoders produce identical results on 12 of the 20 seeds. The MLP is ahead on 6, two of them seeds where AXIOM collapsed (8002, 8010) and four where AXIOM kept 56% to 95% compliance. AXIOM is ahead on 2, where the MLP kept 78% and 87%. The point estimates favour the MLP, but 20 seeds do not separate the encoders at thirty-seven gNBs; M101 adds 20 seeds.
