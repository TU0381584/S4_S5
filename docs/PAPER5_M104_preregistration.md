# M104: is AXIOM's deficit to the MLP a checkpointing artefact? (pre-registration)

Committed on 2026-11-11, before any M104 run and before any M102 or M103 result was read.

## Why

An exploratory diagnosis on stored runs (no new training; recorded in docs/PAPER5_M104_diagnosis.md) found that AXIOM's collapsed runs at 37 gNBs did not fail to learn. In their last 50 training episodes they blocked as many mMTC requests per episode as the healthy runs. Within the final training episode their greedy mMTC decision switched between shedding and accepting, and the checkpoint, taken at the last training step, happened to sit in an accepting phase. Greedy evaluation of that checkpoint blocks nothing, on the evaluation stream and on the training stream alike, while a healthy run's checkpoint blocks mMTC on both. The MLP encoder never collapsed in 40 runs at 37 gNBs, and its whole lead there came from AXIOM's collapsed runs. M67 already diagnosed the same failure at three gNBs and wrote a validation-based checkpoint selection (m67_run.py, V1), applied equally to every value-based arm.

M104 asks whether, with that same selection applied to both encoders, AXIOM's graph-attention encoder ties or beats the MLP where it now ties or loses. The same runs also give the last-checkpoint result, as every reported campaign evaluates it.

## Runs

- Runner experiments/scripts/m104_run.py: the M102 variant named in M102_VARIANT, trained exactly as m64_run.py trains AXIOM, with m67_run.run_learned_selected (V1, unchanged). It takes snapshots at episodes 100, 125, ..., 300, scores each greedily on 10 episodes of validation stream 20000 + seed, evaluates the best (ties to the later) on the usual held-out stream 5000 + seed into eval/, and the last checkpoint into eval_last/. At 37 gNBs m73_run.install() supplies the layout and config.
- Arms: gat (the current AXIOM) and mlp (the current MLP variant).
- Settings: Env A, 37 gNBs, hex; Env B, 7 gNBs, ring.
- Fresh seeds 9940 to 9959 (20), with validation streams 29940 to 29959 and evaluation streams 14940 to 14959, none of which appears in any launch record or result folder.
- cwd framework/, OMP_NUM_THREADS=MKL_NUM_THREADS=OPENBLAS_NUM_THREADS=1, M63_BACKLOG_RESET=1, M64_AXIOM_V2=1, at most 5 jobs at a time, started after M103 finishes. 2 x 2 x 20 = 80 jobs. Output m104/<setting>/<variant>.

## Criteria (two-sided Wilcoxon signed-rank, zero_method wilcox, paired by seed)

- G1, selected checkpoints: gat minus mlp, on reward per step and priority-slice compliance, in both settings; Holm over these 4 tests. Each reported as attention ahead, MLP ahead (Holm p < 0.05) or within chance.
- G2, last checkpoints on the same runs: the same 4 tests, Holm over them, same three-way verdicts.
- G3, collapse: collapsed runs per arm and setting under both checkpoint choices, with Wilson 95% intervals; for gat, collapsed with last against collapsed with selected checkpoints on the same runs, exact McNemar test.
- Reading fixed here: the deficit is called a checkpointing artefact if, in a setting where G2 has the MLP ahead on a measure, G1 has that measure within chance or attention ahead. Attention "beats the MLP under selection" only if G1 has it ahead on reward in at least one setting and behind on neither measure in either setting.
- Reported for every test: 95% bootstrap CIs of the mean paired difference (10,000 resamples, default_rng(0)), medians, wins/ties/losses.
- Analysis: experiments/scripts/m104_analysis.py, written after this commit and before any M104 result is read.

## What this does and does not license

Checkpoint selection is a training-procedure change. Under the paper's M67 rule 3, adopting it in the manuscript means applying it to every value-based arm, the DQN baselines included, and rerunning every campaign. M104 only tests whether it changes the encoder comparison. Nothing changes the manuscript, which changes only after the author reviews the results.
