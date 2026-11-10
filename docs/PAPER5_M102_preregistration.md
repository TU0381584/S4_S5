# M102 and M103: a fair encoder study (pre-registration)

Committed on 2026-11-11, before any M102 or M103 run. Fresh-seed tests (M98 to M101) found that a per-node MLP encoder ties AXIOM's graph-attention encoder in Env A, at 3 and 37 gNBs, and out-earns it in Env B at seven gNBs (+1.13 reward per step over 70 seeds). The author asked whether AXIOM can be modified to beat the MLP. This study gives the attention encoder a fair chance: a small fixed set of attention variants and an equal set of MLP variants, tuned on pilot seeds only, with a selection rule fixed here, then a confirmation of the two selected encoders on fresh seeds. Every variant tried and every result is reported whether it favours attention or not. Nothing here changes the manuscript, which changes only after the author reviews the results. Adopting a new encoder in the paper would require rerunning every AXIOM campaign; that decision is the author's.

## Variants (experiments/scripts/m102_variants.py; every variant keeps the M64 raw-feature skip, per-slice Q-heads of hidden 32 and learning rate 1e-3; execution parameters at seven gNBs in brackets)

Attention family:
- gat: the current AXIOM, a two-layer, four-head GAT, hidden and output 16 (7,782).
- gated: per-node MLP embedding plus a learned scalar gate, initialised at zero, times the GAT embedding. It starts as the MLP and adds neighbour information only as far as training finds it useful (8,279).
- concat: per-node MLP embedding and GAT embedding side by side (9,814).
- gat1: a one-layer GAT (3,430).

MLP family:
- mlp: the current MLP variant, hidden and output 16 (3,190).
- mlp_h32: hidden 32 (3,638).
- mlp_deep: two hidden layers of 16 (3,494).
- mlp_out32: output 32 (5,030).

Each family has four configurations, so both get the same tuning budget. Every parameter count is fixed at every cluster size.

## M102, pilot (cwd framework/, OMP_NUM_THREADS=MKL_NUM_THREADS=OPENBLAS_NUM_THREADS=1, M63_BACKLOG_RESET=1, M64_AXIOM_V2=1, at most 5 jobs at a time)

- Runner: experiments/scripts/m102_run.py, which sets m64_run.AxiomV2Policy to the variant named in M102_VARIANT and runs m64_run.main() with --arm axiom2. At 37 gNBs it first applies m73_run.install(), as M73 and M96 did.
- Pilot seeds 2100 to 2103, which appear in no launch record or result folder.
- Settings: Env B, 7 gNBs, ring (--n 7 --topology ring), where the MLP leads; Env A, 37 gNBs, hex (--env A --n 37 --topology hex), the paper's headline size. 8 variants x 2 settings x 4 seeds = 64 jobs. Output m102/<setting>/<variant>.
- Selection rule (experiments/scripts/m102_select.py, written after this commit and before any pilot result is read): in each family, the variant with the highest mean, over the two settings, of the mean reward per gNB per step on the four pilot seeds. Exact ties go to the current configuration (gat or mlp). The pilot is used only for selection; no pilot result is reported as a finding.

## M103, confirmation

- The two selected variants on fresh seeds 9980 to 9999 (20), which appear in no launch record or result folder, in three settings: Env B 7 ring, Env B 7 hex, Env A 37 hex. 2 x 3 x 20 = 120 jobs. Output m103/<setting>/<variant>.
- If a selected variant is the current gat or mlp configuration, it is still rerun on the fresh seeds so both arms come from the same runner.
- Criteria (two-sided Wilcoxon signed-rank, zero_method wilcox, paired by seed, Holm over the six tests): selected attention variant minus selected MLP variant, on reward per step and on priority-slice compliance, in each setting. Each test is reported as attention ahead, MLP ahead (Holm p < 0.05) or within chance. Reported beside them: 95% bootstrap CIs of the mean paired difference (10,000 resamples, default_rng(0)), medians, wins/ties/losses, collapsed runs per arm with Wilson 95% intervals, and execution parameter counts.
- Reading fixed here: attention "beats the MLP" only if it is ahead on reward in at least one setting and behind on neither measure in any setting.
- Analysis: experiments/scripts/m103_analysis.py, written after this commit and before any M103 result is read.

## What changes if a criterion fails or holds

Nothing automatically. The results and a proposed wording are reported to the author.
