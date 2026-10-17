# M66 verification plan: reproducibility, fresh seeds, and independent recomputation

Committed on 2026-10-17, before any M66 run. Its purpose is to check that every result in the WPC manuscript (commit ef8f8bf) is reproducible, authentic, and accurately reported. All M66 output goes to experiments/results/m66_*. Nothing in the reported campaigns is modified.

## V1, Reproducibility: same seeds, fresh processes, separate directories

| Environment | Arm(s) | Seeds |
|---|---|---|
| Env B, N=3 | AXIOM v2 | 900-904 |
| Env B, N=3 | MAPPO | 900-904 |
| Env B, N=3 | independent DQN, single-agent DQN | 900-902 |
| Env B, N=3 | rule_static, rule_local (selection rerun included) | 900-929 |
| Env A, N=3 | AXIOM v2 | 900-904 |
| Env A, N=19 ring | AXIOM v2 | 900-901 |
| Env B, N=7 ring | AXIOM v2 MLP | 900-902 |
| Env A federated | sigma 0 | 900-901 |
| Env A disruption | AXIOM dropout cell | 900-909 |

**Prediction:** every arm reproduces its stored per-seed reward exactly, to 1e-9. The exception is the single-agent DQN, which the manuscript already states is not bit-reproducible; for it we report the size of the run-to-run differences. Any other mismatch is a reproducibility failure and will be reported as such.

## V2, Generalisation: fresh seeds 3000+, never used before

| Environment | Seeds | Arms | What must hold for the manuscript's claims to stand |
|---|---|---|---|
| Env A, N=3 | 3000-3019 | AXIOM v2, independent DQN, single-agent DQN, MAPPO, oracle rule | AXIOM within 2% of the oracle reward. AXIOM beats the independent DQN and MAPPO, paired Wilcoxon p < 0.05. The single-agent comparison is not predicted, since it was not significant on 30 seeds. |
| Env A, N=19 ring | 3000-3014 | AXIOM v2, independent DQN, single-agent DQN, MAPPO | AXIOM priority-slice SLA ≥ 90% and every baseline ≤ 75%. AXIOM beats each baseline, p < 0.05. |
| Env B, N=3 | 3000-3019 | AXIOM v2, independent DQN, single-agent DQN, MAPPO, rule_static, rule_accept_all, rule_local, rule_neighbour | AXIOM beats rule_static and rule_accept_all. AXIOM beats each learned baseline in mean reward. rule_local beats AXIOM. |
| Env B, N=7 ring | 3000-3009 | AXIOM v2, AXIOM v2 MLP, independent DQN, single-agent DQN, MAPPO, rule_static, rule_local | rule_local beats every learned arm. AXIOM shows no significant advantage over the MLP encoder. |

Every V2 check is reported whether it holds or fails.

## V3, Independent recomputation: new code, written without reusing the analysis scripts

Script: m66_verify.py.
- It parses the raw evaluation logs with its own reader.
- It recomputes per-seed reward, block precision, collapse, and per-slice SLA.
- It recomputes the paired Wilcoxon tests and the Holm correction with an independent implementation.
- It checks every number quoted in the manuscript's Results tables and key sentences against the recomputation, with tolerances stated per quantity.

## V4, Integrity checks

- Evaluation streams (5000 + seed) never coincide with any training or rule-selection stream.
- Seed sets are disjoint where the manuscript says they are disjoint.
- The DP epsilon values are recomputed from the logged noisy-step counts with an independent implementation of the zCDP formula.
- Every figure's plotted numbers agree with the text.

## Addendum 1, M66b: further fresh seeds (committed 2026-10-17, after M66 and before any M66b run)

M66 left two reported claims without a fresh-seed check: Env A scaling at seven gNBs, and the absence of a significant federated cost. It also checked only the ring layout at nineteen gNBs. M66b retrains on fresh seeds 3000-3009, which no Env A N=7, N=19 hex, or federated run has used. Output goes to experiments/results/m66b_fresh.

| Cell | Arms | What must hold for the manuscript's claims to stand |
|---|---|---|
| Env A, N=7, ring and fully-connected | AXIOM v2, independent DQN, single-agent DQN, MAPPO | AXIOM priority-slice SLA ≥ 90% pooled over both layouts, and each baseline ≤ 80%. AXIOM beats each baseline on priority SLA and on reward under both layouts. All 12 comparisons hold at Holm-adjusted p < 0.05. |
| Env A, N=19, hex | same four arms | AXIOM priority-slice SLA ≥ 90%, and each baseline ≤ 75%. AXIOM beats each baseline on priority SLA and on reward. All 6 comparisons hold at Holm-adjusted p < 0.05. |
| Env A, N=3, federated sigma 0 | FedAvg AXIOM vs centralised AXIOM v2 (m66_fresh/A_n3, same seeds) | No significant difference in reward, paired Wilcoxon p ≥ 0.05. The difference and its bootstrap CI are reported either way. |

Every M66b check is reported whether it holds or fails.
