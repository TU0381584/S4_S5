# M104: is AXIOM's deficit to the MLP a checkpointing artefact? (results, 2026-11-11)

Pre-registration: docs/PAPER5_M104_preregistration.md (934e5d69). Analysis: experiments/scripts/m104_analysis.py (55323281), both committed before any M104 result was read. Output: experiments/results/m104/analysis.json. All 80 jobs exited 0 (10:36 to 14:39).

Arms: gat (the current AXIOM, 7,782 execution parameters) and mlp (the current MLP variant, 3,190). The stored checkpoints differ by 4,592 parameters, which confirms each arm ran its own encoder. Seeds 9940 to 9959. Every run is evaluated twice on the held-out stream: the checkpoint chosen by M67's validation rule (eval/) and the last checkpoint (eval_last/).

## G1, selected checkpoints (gat minus mlp, Holm over 4)

| Setting | Measure | Mean diff | 95% CI | p | Holm p | W/T/L | Verdict |
|---|---|---|---|---|---|---|---|
| Env A 37 hex | reward | 0.000 | [0, 0] | 1 | 1 | 0/20/0 | within chance |
| Env A 37 hex | compliance (pp) | 0.000 | [0, 0] | 1 | 1 | 0/20/0 | within chance |
| Env B 7 ring | reward | -0.988 | [-1.779, -0.200] | 0.0328 | 0.131 | 6/0/14 | within chance |
| Env B 7 ring | compliance (pp) | -6.219 | [-11.910, -0.632] | 0.040 | 0.131 | 6/0/14 | within chance |

## G2, last checkpoints on the same runs (Holm over 4)

| Setting | Measure | Mean diff | 95% CI | p | Holm p | W/T/L | Verdict |
|---|---|---|---|---|---|---|---|
| Env A 37 hex | reward | +5.335 | [+2.348, +8.638] | 0.0117 | 0.0352 | 8/12/0 | attention ahead |
| Env A 37 hex | compliance (pp) | +10.100 | [+3.648, +18.291] | 0.0117 | 0.0352 | 8/12/0 | attention ahead |
| Env B 7 ring | reward | -1.223 | [-2.037, -0.343] | 0.00427 | 0.0171 | 2/1/17 | MLP ahead |
| Env B 7 ring | compliance (pp) | -7.808 | [-13.700, -1.536] | 0.0386 | 0.0386 | 6/2/12 | MLP ahead |

## G3, collapse

No run collapsed in either setting, for either encoder, under either checkpoint choice: 0 of 20 everywhere (Wilson 95% [0, 16.1]%). McNemar has no discordant pairs (p = 1).

## Pre-registered readings

- Checkpointing artefact: the rule is met in Env B 7 ring on both measures. The MLP is ahead with last checkpoints and within chance with selected checkpoints.
- Attention beats the MLP under selection: no. It is not ahead on reward in either setting.

## What the numbers say, beyond the verdicts

1. At 37 gNBs the two encoders learn the same policy. With selection, all 20 seed pairs give identical rewards and compliance. Each seed's best validation score is also identical across the two encoders: 20 distinct values, one per validation stream, matched exactly. Most snapshots from episode 100 onward sit at that maximum. The two encoders differ only in where training happens to stop. On these seeds the MLP's last checkpoint fell below its best in 8 of 20 runs (rewards 156.7 to 175.7, none flagged collapsed), and AXIOM's in 1 of 20. That is the reverse of M100 and M101, where AXIOM's last checkpoints were the weaker ones (5 of 40 collapsed, the MLP 0 of 40). Last-checkpoint comparisons at 37 gNBs therefore track which run stops on a bad step, in either direction. They do not reflect a difference in what the encoders learn.
2. In Env B 7 ring the artefact verdict is weak and should not be read as parity. The selected-checkpoint estimate keeps the same sign and most of its size (-0.99 against -1.22 reward), its bootstrap CI still excludes zero, and the MLP still wins 14 of 20 seeds. The verdict changes because the raw p of 0.033 fails Holm over four tests. The MLP's Env B advantage seen in M67, M99 and M103 is reduced by checkpoint selection, not removed.
3. Selection picked earlier checkpoints for AXIOM in Env B (median episode 250, as early as 125) than for the MLP (median 275). This is consistent with AXIOM peaking earlier and drifting in Env B.
4. End-of-training instability (descriptive, experiments/scripts/m104_instability_diag.py, same measure as diagnosis items 4 and 5). In M104's 37-gNB training logs AXIOM switches in 17 of 20 runs (median 4, 13% accepting steps) and the MLP in 15 of 20 (median 2, 7%). The direction of item 4 holds. Even so, the MLP's last checkpoints were the weaker ones here, so this training-time measure, taken with exploration on, does not predict which last checkpoint evaluates badly. Item 4 should be read as a tendency, not a mechanism.

## Consequences for the paper (proposed, for the author)

- The encoder question is now settled as far as these campaigns can settle it. No attention design beat the MLP (M102/M103). With checkpoint selection the two encoders are identical at 37 gNBs and the MLP keeps a reduced lead in Env B. The paper should keep stating that the gain comes from per-gNB sharing with the skip path, and that attention adds no measured benefit.
- The collapses at 37 gNBs that the paper reports for AXIOM are a stopping-point effect, not a failure to learn. M104 shows the same effect hitting the MLP on other seeds. A short sentence could say this, citing M67's rule, without adopting selection.
- Adopting checkpoint selection as the paper's training procedure would need every value-based arm rerun, the DQN baselines included (M67 rule 3). That is the author's decision. M104 does not license it on its own.
- Nothing in main.tex changes until the author reviews M98 to M104.

Disk: M104's snapshots, validation and evaluation folders take 6.0 GB. 13 GB are free. Nothing has been deleted.
