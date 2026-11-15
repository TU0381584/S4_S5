# M109: baseline parity, a parameter-shared baseline, training budget and QMIX (pre-registration)

Committed on 2026-11-16, before any M109 run. Gate 4 of the pre-submission review (CHANGELOG_WPC.md).

## Why

A pre-submission review asked whether AXIOM's lead at scale survives four checks. The DQN baselines differ from AXIOM in their loss and normalisation. No baseline shares its parameters across gNBs without AXIOM's encoder and per-slice heads. The baselines may only need more training. QMIX is a standard value-factorisation method that the paper does not run.

The design asked for needs about 14 CPU-hours per seed, over the 72 CPU-hour limit set for this gate. This is the reduced design the author approved on 2026-11-16, about 70 CPU-hours.

## Runs

- **Seeds:** 13000 to 13009, never used before. Evaluation streams are 18000 to 18009 (offset 5000). The budget study uses 13000 to 13004.
- **Runner:** experiments/scripts/m109_run.py, which is m64_run.py (m73_run.py at 37 gNBs) with one variant swapped in at run time. The framework and the earlier runners are not edited. The new arms are in experiments/scripts/m109_arms.py.
- **Settings as in the paper:** 300 training and 50 evaluation episodes, last checkpoint, OMP/MKL/OPENBLAS threads 1, M63_BACKLOG_RESET=1, M64_AXIOM_V2=1, six jobs at a time. Env A on the hex layout unless stated.
- **DQN-SA** is seeded in every M109 run, as it already is at 37 gNBs.
- **No tuning.** Every new arm uses the value-based learners' learning rate of 0.001 and exploration schedule unchanged. No arm is tuned on these seeds.
- **Job list:** experiments/logs/m109/jobs.txt, 240 jobs, written by m109_analysis.py --jobs.

| Arm | What it is | Settings | Seeds |
|---|---|---|---|
| AXIOM | the paper's AXIOM, for paired tests | 7, 19, 37 gNBs, and Env B at 3 | 10 |
| Parity DQN-SA, parity DQN-I | the baselines with Huber loss and a LayerNorm after each hidden layer. Their gradient norm was already clipped at 1.0 | 7, 19, 37 gNBs | 10 |
| Parameter-shared | one MLP Q-network for all gNBs, own-row features and the slice one-hot as input, two hidden layers of 128, one head, trained as AXIOM is | 7, 19, 37 gNBs, and Env B at 3 | 10 |
| MLP encoder | the paper's per-node encoder variant | 7, 19, 37 gNBs | 10 |
| Shared head | the paper's variant with one head for all slices | 7, 19, 37 gNBs | 10 |
| QMIX | the parameter-shared agent network trained with a QMIX target, each gNB's utility being the sum of its chosen Q-values | 19 gNBs | 10 |
| Budget | AXIOM, DQN-SA and DQN-I trained for 1,500 episodes and also evaluated from the checkpoints saved at 300 and 900. MAPPO has no checkpoint hook, so it gets separate runs of 300, 900 and 1,500 episodes | 19 gNBs | 5 |

## Analysis

experiments/scripts/m109_analysis.py is committed with this file. Tests are two-sided Wilcoxon signed-rank tests on paired seeds, with ties within 1e-9 dropped. Each result carries the 95% bootstrap CI of the mean paired difference, the Hodges-Lehmann estimate and the matched-pairs rank-biserial correlation. Holm correction is applied within each family. Priority-slice compliance is the mean of URLLC and eMBB compliance, at cluster level. A run is collapsed when it blocks no request.

| Family | Comparisons, each AXIOM minus the arm, on compliance and on reward | Tests |
|---|---|---|
| P1 parity | parity DQN-SA and parity DQN-I at 7, 19, 37 gNBs | 12 |
| P2 parameter-shared | the parameter-shared baseline at 7, 19, 37 gNBs and in Env B at 3 | 8 |
| P3 ablations | MLP encoder and shared head at 7, 19, 37 gNBs | 12 |
| P5 QMIX | QMIX at 19 gNBs | 2 |

P4, the budget study, is descriptive. With five paired seeds a signed-rank test cannot reach p < 0.05, so it reports each policy's compliance, reward and collapse count at 300, 900 and 1,500 episodes with bootstrap CIs, and no significance claim.

QMIX stability is judged per seed. A run is stable if every training loss is finite and the mean loss of its last 20 episodes is at most twice its lowest 20-episode mean. Its results are reported whether or not it is stable, with its loss curves.

## Predictions and what would change the paper

- **Stop rule.** If the mean priority-slice compliance of a parity baseline or of the parameter-shared baseline comes within 5 points of AXIOM's at 19 or 37 gNBs, work stops and the result is reported to the author before any text changes, because the paper's headline would change.
- **P1.** If the parity baselines stay more than 5 points below AXIOM at 19 and 37 gNBs with Holm p < 0.05, the paper's lead over the DQN baselines is not an artefact of their loss or normalisation.
- **P2.** If the parameter-shared baseline matches AXIOM, parameter sharing alone explains the scaling result and the paper must say so. If it falls short, the per-slice heads or the encoder add to it.
- **P3.** The paper states that the shared head fails at scale and the MLP encoder does not. Either may fail to hold here.
- **P4.** If the baselines' compliance rises towards AXIOM's with more episodes, their collapse is a budget effect and the paper must say so.

Every result is reported whatever its outcome. The original, untuned baselines are not rerun on these seeds, so a parity baseline is compared with AXIOM on the same seeds and with the paper's original baseline only descriptively.

## What follows

The manuscript does not change until the author has seen the results.
