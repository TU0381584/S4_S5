# M101: attention at thirty-seven gNBs, twenty more seeds (pre-registration)

Committed on 2026-11-10, before any M101 run. M100 found the MLP encoder within chance of AXIOM at thirty-seven gNBs in Env A on 20 seeds (Holm p = 0.14 on both measures), with point estimates favouring the MLP. M101 adds 20 fresh seeds to decide the question at the size of the paper's headline result. Every result is reported whether it holds or fails, and nothing here changes the manuscript. Output: experiments/results/m101/. Analysis: experiments/scripts/m101_analysis.py, written after this commit and before any M101 result is read.

## Runs

- Fresh seeds 9960 to 9979, which appear in no launch record and no result folder (checked before this commit).
- m73_run.py --arm axiom2 and --arm axiom2_mlp --env A --n 37 --topology hex, cwd framework/, OMP_NUM_THREADS=MKL_NUM_THREADS=OPENBLAS_NUM_THREADS=1, M63_BACKLOG_RESET=1, M64_AXIOM_V2=1, at most 5 jobs at a time. Output m101/A_n37_hex. 40 jobs.

## Criteria (two-sided Wilcoxon signed-rank, zero_method wilcox, paired by seed; Holm within each family of two: compliance and reward)

- F1. MLP minus AXIOM on the 20 fresh seeds. Each test is reported as MLP ahead, AXIOM ahead (Holm p < 0.05) or within chance.
- F2. The same on 40 seeds pooled (M101 and M100's 8000 to 8019, AXIOM from m96/A_fresh/n37_hex). Same three-way verdict.
- Reported: 95% bootstrap CIs of the mean paired difference, medians, wins/ties/losses, collapsed runs per arm with Wilson 95% intervals.
- The paper's sentence "A per-node MLP encoder ties AXIOM in Env A" is judged against F2: if both F2 tests are within chance the tie stands at thirty-seven gNBs; if the MLP is ahead on either, the sentence must say so.

## What changes if a criterion fails or holds

Nothing automatically. The results and a proposed wording are reported to the author.
