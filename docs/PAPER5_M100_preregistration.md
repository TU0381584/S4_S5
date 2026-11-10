# M100: the two ablations at thirty-seven gNBs (pre-registration)

Committed on 2026-11-10, before any M100 run. M99 confirmed on fresh seeds that the per-slice heads matter at nineteen gNBs and that an MLP encoder out-earns graph attention in Env B at seven gNBs. Neither ablation has been run at thirty-seven gNBs, the size of the paper's headline result. M100 runs both variants at that size against AXIOM runs already stored for the same seeds. Every result is reported whether it holds or fails, and nothing here changes the manuscript, which changes only after the author reviews the results. Output: experiments/results/m100/. Analysis: experiments/scripts/m100_analysis.py, written after this commit and before any M100 result is read.

## Design

- AXIOM side, no new runs: m96/A_fresh/n37_hex, seeds 8000 to 8019 (M96 a, pre-registered 32de84d0), trained by m73_run.py --arm axiom2 --env A --n 37 --topology hex with M63_BACKLOG_RESET=1 M64_AXIOM_V2=1. Opened only to count seeds (20) and to read the median training time (979 s); no difference between policies was computed.
- MLP variant, new: m73_run.py --arm axiom2_mlp --env A --n 37 --topology hex, the same seeds and environment. Output m100/A_n37_hex.
- Shared-head variant, new: experiments/scripts/m100_sharedhead_n37.py, a new five-line wrapper that calls m73_run.install() (the 37-gNB layout and config) and sets m64_run.AxiomV2Policy to m70_run.SharedHeadAxiom (the M70 variant), then m64_run.main(). Neither imported module is modified. Same seeds and environment. Output m100/A_sharedhead_n37_hex.
- cwd framework/, OMP_NUM_THREADS=MKL_NUM_THREADS=OPENBLAS_NUM_THREADS=1, at most 5 jobs at a time; 300 training episodes, 50 evaluation episodes on the held-out stream 5000 + seed. About 40 jobs at roughly 1,000 s each.

## Criteria (two-sided Wilcoxon signed-rank, zero_method wilcox, paired by seed; Holm within each family of two)

- E1. Per-slice heads at thirty-seven gNBs: AXIOM minus shared head on priority-slice compliance and on reward per step. HOLDS if both are positive at Holm-adjusted p < 0.05. Reported beside it: collapsed runs per arm with Wilson 95% intervals.
- E2. Attention at thirty-seven gNBs in Env A: MLP variant minus AXIOM on priority-slice compliance and on reward per step. Each test is reported as MLP ahead, AXIOM ahead (Holm p < 0.05 in that direction) or within chance. The paper's sentence "A per-node MLP encoder ties AXIOM in Env A" is judged against these two verdicts.
- Reported for both: 95% bootstrap CIs of the mean paired difference (10,000 resamples, default_rng(0)), medians, wins/ties/losses.

## What changes if a criterion fails or holds

Nothing automatically. The results and a proposed wording are reported to the author, who decides what enters the paper.
