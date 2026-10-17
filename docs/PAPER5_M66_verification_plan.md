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

## Addendum 2, M66c: remaining fresh-seed checks (committed 2026-10-18, after M66b and before any M66c run)

M66c covers every reported claim that M66 and M66b left without a fresh-seed or properly seeded check. Output goes to experiments/results/m66c_fresh. Every check is reported whether it holds or fails, and nothing here replaces the M66b result for Env A at seven gNBs fully-connected, which stays reported as failed.

Two facts were established before this addendum, from reruns of stored seeds only. First, under each Env A sensitivity condition the stored oracle equals the static shed-mMTC rule exactly on seeds 900-909, so rule_static is the oracle here. Second, the wrapper m66c_seeded_single.py, which seeds torch immediately before the single-agent DQN builds its network, gives identical results for seeds 900 and 901 in two separate processes.

| ID | Cell | Seeds | Arms | What must hold |
|---|---|---|---|---|
| C1 | Env A, N=7, hex | 3000-3009 | AXIOM v2, independent DQN, single-agent DQN, MAPPO | AXIOM priority SLA ≥ 90%, each baseline ≤ 80%. AXIOM beats each baseline on reward and on priority SLA, all 6 at Holm-adjusted p < 0.05. |
| C2 | Env A, N=19, fully-connected | 3000-3009 | same four | AXIOM priority SLA ≥ 90%, each baseline ≤ 75%. All 6 comparisons at Holm-adjusted p < 0.05. |
| C3 | Env A, N=7, fully-connected, larger sample | 4000-4019 | same four | Same criteria as C1. This is a separate, larger replication of the cell that failed in M66b. It is reported alongside that failure, never in place of it. |
| C4 | Env B, N=7, fully-connected and hex | 3000-3009 | AXIOM v2, AXIOM v2 MLP, independent DQN, single-agent DQN, MAPPO, rule_static, rule_local | Under each layout, rule_local's mean reward exceeds every learned arm's. AXIOM shows no significant advantage over the MLP encoder, on reward or priority SLA. AXIOM's reward is not significantly above the static rule's. |
| C5 | Env A disruption, frozen fresh checkpoints | 3000-3009 | AXIOM v2, independent DQN, single-agent DQN (from M66 fresh A_n3), FedAvg AXIOM sigma 0 (from M66b) | Every dropout and churn cell lowers every arm's normalised reward, Holm-adjusted p < 0.05. No gap between AXIOM and any baseline in disruption cost survives Holm correction. AXIOM's block precision under spikes ≥ 0.95. |
| C6 | Env A federated DP | 3000-3009 | sigma 0.5, 1, 2, 4 | Mean reward is below centralised AXIOM (M66 fresh A_n3) at every sigma. None of the four drops survives Holm correction. Each client takes 17,969 noisy steps, so the quoted epsilon values apply. |
| C7 | Single-agent DQN properly seeded | Env A and Env B N=3, 900-929 and 1000-1009; Env A N=19 ring, the 30 reported seeds | single-agent DQN through m66c_seeded_single.py | Env B N=3: AXIOM still beats it at Holm-adjusted p < 0.05 within the reported three-baseline family. Env A N=19: AXIOM still beats it on priority SLA at p < 0.05. Env A N=3 comparisons and collapse counts are reported, not predicted. |
| C8 | Env A sensitivity | 3000-3009 | AXIOM v2, rule_static, independent DQN, single-agent DQN under load102, load107, weights | In each condition, AXIOM is within 2% of the oracle's reward and not significantly different from it, and AXIOM's mean reward exceeds both DQN baselines'. |
| C9 | Env B sensitivity, N=3 | 3000-3009 | original AXIOM, AXIOM v2 at LR 3e-4 and 3e-3, wide AXIOM v2, all against AXIOM v2 from M66 fresh B_n3 | The original AXIOM earns less than AXIOM v2 in at least 9 of 10 seeds, p < 0.05. LR 3e-3 and the wide encoder show no significant difference from AXIOM v2. |
