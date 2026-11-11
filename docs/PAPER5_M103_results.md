# M102 pilot and M103 confirmation: can a modified attention encoder beat the tuned MLP? (results, 2026-11-11)

Pre-registration: docs/PAPER5_M102_preregistration.md (covers M102 and M103). Analysis: experiments/scripts/m102_select.py and m103_analysis.py, both committed before any M102 or M103 result was read. Output: experiments/results/m102/selection.json, experiments/results/m103/analysis.json. All 64 M102 jobs and all 120 M103 jobs exited 0.

## M102 pilot (selection only, not a finding)

Eight encoders, four per family, on pilot seeds, scored by mean reward per gNB per step over Env B 7 ring and Env A 37 hex. The pre-registered rule picks the best of each family.

| Variant | Family | Exec. params | B 7 ring | A 37 hex (collapsed) | Score |
|---|---|---|---|---|---|
| gat (current AXIOM) | attention | 7,782 | 3.316 | 4.467 (1) | 3.8915 |
| gated (MLP + gated GAT) | attention | 8,279 | 3.370 | 4.797 (0) | 4.0832 |
| concat (MLP and GAT side by side) | attention | 9,814 | 3.411 | 4.797 (0) | 4.1038 |
| gat1 (one GAT layer) | attention | 3,430 | 3.401 | 4.652 (0) | 4.0264 |
| mlp (current MLP variant) | MLP | 3,190 | 3.642 | 4.797 (0) | 4.2193 |
| mlp_h32 | MLP | 3,638 | 3.583 | 4.797 (0) | 4.1896 |
| mlp_deep | MLP | 3,494 | 3.639 | 4.724 (0) | 4.1814 |
| mlp_out32 | MLP | 5,030 | 3.766 | 4.652 (1) | 4.2090 |

Selected: concat for attention, mlp for the MLP. Every MLP variant scored above every attention variant on the pilot.

## M103 confirmation (fresh seeds 9980 to 9999, concat minus mlp, two-sided Wilcoxon, Holm over 6 tests)

| Setting | Measure | Mean diff | 95% CI | p | Holm p | W/T/L | Verdict |
|---|---|---|---|---|---|---|---|
| Env B 7 ring | reward | +0.173 | [-0.964, +1.542] | 0.717 | 1 | 10/1/9 | within chance |
| Env B 7 ring | compliance (pp) | -2.518 | [-9.221, +4.295] | 0.717 | 1 | 10/1/9 | within chance |
| Env B 7 hex | reward | -1.216 | [-1.981, -0.402] | 0.0107 | 0.0534 | 5/0/15 | within chance |
| Env B 7 hex | compliance (pp) | -10.842 | [-15.978, -5.264] | 0.00233 | 0.014 | 5/0/15 | MLP ahead |
| Env A 37 hex | reward | -5.057 | [-9.513, -1.074] | 0.0929 | 0.372 | 3/12/5 | within chance |
| Env A 37 hex | compliance (pp) | -8.724 | [-16.722, -1.671] | 0.0929 | 0.372 | 3/12/5 | within chance |

Collapsed runs (Wilson 95%): Env B ring and hex, 0 of 20 for both arms. Env A 37 hex, concat 4 of 20 [8.1, 41.6]%, mlp 0 of 20 [0, 16.1]%.

Pre-registered reading: attention beats the MLP only if ahead on reward in at least one setting and behind on neither measure in any setting. Result: no. The best attention variant does not beat the MLP. It falls behind on compliance in Env B 7 hex, and it ties elsewhere.

## Descriptive notes (not tests)

- At 37 gNBs, 12 of 20 seed pairs give identical rewards: both encoders reach the same policy. All 5 concat losses there are runs near 156 reward per step (seeds 9980, 9983, 9984, 9985, 9986) against about 177 for the MLP; 4 are flagged collapsed and 9985 falls just short of the flag. This is the same failure as the current AXIOM at 37 gNBs, so adding a local MLP path beside the GAT did not remove it.
- In Env B the MLP's advantage shows in hex, where M99 also found it, and not in ring on these seeds.

## What this means for the paper

Within this search (4 attention designs against 4 MLP designs, same training budget), no attention encoder beat the MLP. The paper's current position, that the gain comes from per-gNB sharing with the skip path and not from attention, is strengthened. The remaining open question is whether the attention deficit is only a checkpointing artefact, which M104 tests (running since 10:36). Nothing in the manuscript changes until the author reviews these results.
