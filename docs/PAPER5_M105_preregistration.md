# M105: does checkpoint selection change the paper's AXIOM-versus-DQN verdicts at scale? (pilot pre-registration)

Committed on 2026-11-12, before any M105 run.

## Why

M104 found that at 37 gNBs the differences between AXIOM's encoders under the last checkpoint come from where training stops. A fix for that, M67's validation-based checkpoint selection (V1), is a training-procedure change. Under M67 rule 3 it would have to be applied to every value-based arm: AXIOM, the single-agent DQN (DQN-SA) and the independent DQN (DQN-I). Adopting it in the paper would mean rerunning every campaign with those arms, about 700 runs.

M67 has already tested selection at 3 gNBs in Env A. There, selection lifted DQN-SA almost as much as AXIOM, and AXIOM's lead fell from +0.350 (p 0.036) to +0.046 (p 0.084). The author asked for a pilot before committing to the full rerun. M105 asks whether selection changes any AXIOM-versus-DQN verdict at 7, 19 and 37 gNBs, the sizes M67 did not test.

## Runs

- Runner experiments/scripts/m104_run.py with M102_VARIANT=gat. For axiom2 this is the current AXIOM. The variant does not touch the DQN arms. The runner applies m67_run.run_learned_selected (V1, unchanged) to every arm: snapshots at episodes 100, 125, ..., 300, greedy scoring on 10 episodes of validation stream 20000 + seed, the best snapshot (ties go to the later) evaluated on held-out stream 5000 + seed into eval/, and the last checkpoint into eval_last/. DQN-SA's initialisation is seeded (torch.manual_seed(seed)), as in M67 and M73. At 37 gNBs, m73_run.install() supplies the layout and config.
- Arms: axiom2, single_agent_dqn, independent_dqn.
- Cells:
  - Env A: 7 gNBs hex, 19 gNBs hex, 37 gNBs hex.
  - Env B: 7 gNBs ring, 19 gNBs hex.
- Fresh seeds 10000 to 10009 (10 per cell), with evaluation streams 15000 to 15009 and validation streams 30000 to 30009. None of these appears in any launch record or result folder.
- cwd framework/, OMP/MKL/OPENBLAS threads 1, M63_BACKLOG_RESET=1, M64_AXIOM_V2=1, at most 5 jobs at a time, longest cells first. 5 cells x 3 arms x 10 seeds = 150 jobs. Output m105/<cell>/<arm>/seed<seed>.

## Tests (two-sided Wilcoxon signed-rank, zero_method wilcox, paired by seed)

- L, last checkpoints: AXIOM minus DQN-SA and AXIOM minus DQN-I, on reward per step and priority-slice compliance, in every cell. That is 5 x 2 x 2 = 20 tests, with Holm over the 20.
- S, selected checkpoints: the same 20 tests on the same runs, with Holm over the 20.
- Each test gets a three-way verdict: AXIOM ahead, baseline ahead (Holm p < 0.05) or within chance. Each also reports the mean paired difference, a 95% bootstrap CI (10,000 resamples, default_rng(0)), the median and wins/ties/losses.
- Descriptive, per arm and cell: selected minus last reward, as a mean with wins/ties/losses, plus collapsed runs under each checkpoint choice.

## Decision rule, fixed here

The full rerun under selection is called needed if either of the following holds:

1. Verdict change: any of the 20 tests has a different verdict under S than under L.
2. Lead erosion: in a cell and measure where L has AXIOM ahead of a baseline, AXIOM's mean lead under S is less than half its mean lead under L. This is the M67 three-gNB pattern.

Otherwise the full rerun is called not needed. The paper could then report selection as a robustness check, citing M67 and M105, without replacing its numbers.

## Limits stated in advance

- Ten seeds per cell is a pilot. A verdict that is "within chance" under both S and L does not show the two procedures agree, only that neither detects a difference. The decision rule is deliberately sensitive: either a verdict change or a halved lead triggers the full rerun.
- MAPPO is not value-based and is outside rule 3. It is not run.
- Three gNBs is not rerun. M67's result stands there.

## Analysis

experiments/scripts/m105_analysis.py, committed with this file and before any M105 result is read. The manuscript does not change, whatever the outcome, until the author reviews it.
