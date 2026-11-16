# M109: baseline parity, parameter sharing, ablation variants, QMIX and training budget (results)

These are the results for docs/PAPER5_M109_preregistration.md, committed in 497c86d6 before any run. The analysis is experiments/results/m109/analysis.json, produced by m109_analysis.py. Nothing in the analysis was changed after the runs.

## Runs

All 240 of 240 jobs exited 0 (experiments/logs/m109/done.txt, last line "ALL DONE 2026-11-16 09:53:09") and no job log holds a traceback. A laptop reboot at 05:24 killed six running jobs, which were rerun from scratch by the restart-safe launcher. Seeds are 13000 to 13009 (13000 to 13004 for the budget study).

## Stop rule

Not triggered. The closest parity or parameter-shared baseline is 28.9 points below AXIOM in priority-slice compliance at 19 gNBs (parity DQN-SA) and 38.1 points below at 37 gNBs (parameter-shared). Every gap is far above the 5-point threshold.

## Priority-slice compliance and reward (Env A, mean of 10 seeds; collapsed runs in brackets)

| Arm | 7 gNBs | 19 gNBs | 37 gNBs |
|---|---|---|---|
| AXIOM (GAT) | 99.8 % (0) | 96.2 % (1) | 100.0 % (0) |
| Parity DQN-SA | 92.3 % (0) | 67.2 % (8) | 61.2 % (9) |
| Parity DQN-I | 68.5 % (0) | 53.1 % (0) | 28.6 % (0) |
| Parameter-shared MLP | 91.8 % (0) | 66.8 % (10) | 61.9 % (10) |
| MLP encoder | 100.0 % (0) | 89.6 % (0) | 99.9 % (0) |
| Shared head | 98.4 % (0) | 83.5 % (2) | 61.9 % (8) |
| QMIX (shared network) | | 99.9 % (0) | |

In Env B at 3 gNBs AXIOM reaches 65.6 % and the parameter-shared baseline 64.8 %.

## Pre-registered families (two-sided Wilcoxon, Holm within family, n = 10)

- P1, parity baselines: AXIOM is ahead of parity DQN-SA and DQN-I on compliance and reward at 7, 19 and 37 gNBs (all 12 comparisons, Holm p 0.0234, rank-biserial 1.00 for all but ties). The lead over the original DQN baselines is not an artefact of their loss or normalisation.
- P2, parameter-shared baseline: AXIOM is ahead at 7, 19 and 37 gNBs on both measures (Holm p 0.0156 to 0.0195). In Env B at 3 gNBs the compliance difference is within chance (+0.8 points, p 0.375) and the reward lead is small (+0.346, p 0.027). Parameter sharing alone does not explain the scaling result in Env A.
- P3, ablations: the MLP encoder is within chance of AXIOM at 7, 19 and 37 gNBs on both measures. The shared head is within chance at 7 and 19 gNBs and falls behind at 37 gNBs (compliance +38.1 points, reward +21.1, Holm p 0.0234). With 10 seeds the 19-gNB MLP gap (3.8 reward) cannot be told from chance.
- P5, QMIX at 19 gNBs: within chance of AXIOM on both measures (compliance -0.04, reward -0.29, Holm p 1.0). By the pre-registered rule 0 of 10 seeds are stable: every loss is finite, but the last-20-episode mean loss is 4 to 5 times the lowest 20-episode mean in all 10 seeds.

## Training budget (5 seeds, descriptive, 19 gNBs in Env A)

| Arm | 300 episodes | 900 | 1,500 |
|---|---|---|---|
| AXIOM | 100.0 % (0) | 88.9 % (1) | 100.0 % (0) |
| Parity single-agent DQN | 65.2 % (4) | 65.2 % (5) | 65.2 % (5) |
| Parity independent DQN | 51.0 % (0) | 49.0 % (0) | 32.5 % (0) |
| MAPPO | 57.3 % (0) | 56.5 % (0) | 57.1 % (0) |

Longer training does not raise any baseline towards AXIOM, so the baselines' collapse is not a budget effect (P4). Parity independent DQN falls with more episodes.

## What follows

The manuscript is unchanged. The author decides how to report these arms. Items worth deciding: whether the parity baselines replace or supplement DQN-SA and DQN-I in Table 3, whether QMIX is reported given that it fails the stability rule while matching AXIOM on outcome, and whether the MLP-encoder and shared-head arms are reported at the three sizes. The results directory is 43 GB on a disk now at 93 %, so compression with experiments/scripts/gzip_verified.sh needs approval.
