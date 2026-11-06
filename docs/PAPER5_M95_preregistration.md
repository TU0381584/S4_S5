# M95: filling the untested cells of the rule regime map, Fig. 10 (pre-registration)

Committed on 2026-11-06, before any M95 run. The author asked to fill the blank cells of the main paper's Fig. 10, which maps where AXIOM beats or trails a rule tuned once at nominal load. Every cell is run exactly the way its row's existing cells were run, so the two panels stay internally consistent. Nothing here replaces a reported result. Output goes to experiments/results/m95/. The framework is not modified.

## Cells

Env A, panel a, AXIOM against the static rule on priority-slice compliance. The existing load cells (M76 part e, nineteen gNBs, hex) retrained every learned policy under each load, and the static rule needs no tuning. The new cells do the same.
- 3 gNBs (fully-connected, the only layout at that size), 7 gNBs (hex) and 37 gNBs (hex), each at 110% and 120% of each slice's nominal share (M76_LOAD=1.10 and 1.20, the reported Env A uses 1.05).
- AXIOM (axiom2) trained for 300 episodes under the load and evaluated for 50 episodes on the held-out stream, and the static rule evaluated on the same streams. Runner: m76_run.py, through m75_run.py and m73_run.py at 37 gNBs, exactly as the M76 e jobs were run.
- Seeds 900-911 and 1000-1002, as in the existing load cells.

Env B, panel b, AXIOM against the tuned local rule on reward per gNB per step. The existing shifted cells (M72 at 3 and 7 gNBs, M76 b1 at 19) evaluated stored nominal checkpoints and the nominally tuned rule, with neither retrained nor re-tuned. The new cells do the same.
- 7 gNBs, ring: load_0.80, load_1.05 and load_1.15, with m72_shift.py eval on the m64/n7_ring checkpoints and that cell's selected local rule.
- 19 gNBs, hex: load_0.80 and load_1.05, with m76_shift.py on the m75/D_envB_n19_hex checkpoints and the local rule carried from 7 gNBs.
- Seeds 900-911 and 1000-1002.

## Analysis, fixed now

- Each cell is classified as before. The mean paired difference (AXIOM minus rule) per seed, a two-sided Wilcoxon signed-rank test (zero_method wilcox), and Holm correction over all of a panel's cells, so the new cells join each panel's family. A cell is AXIOM-ahead or rule-ahead when its Holm-adjusted p is below 0.05, and a tie otherwise.
- Because the Holm family grows, the verdict of an existing cell can change. Every changed verdict is reported.
- Any sentence of either document that the filled map contradicts is changed to match it. In particular, if any new Env B cell above 100% is not AXIOM-ahead, the statement that AXIOM leads every Env B cell above the tuning load is revised, and if the static rule leads any new Env A cell, the Env A statements are revised.
- No cell is dropped or rerun after its result is read.

## Budget

About 22 CPU-hours for the 90 Env A training runs (median training time 544 s at 3 gNBs, 796 s at 7 and 1,328 s at 37), plus about 10 CPU-minutes of Env B evaluation. At most 5 parallel jobs, OMP_NUM_THREADS=MKL_NUM_THREADS=OPENBLAS_NUM_THREADS=1, longest jobs first.
