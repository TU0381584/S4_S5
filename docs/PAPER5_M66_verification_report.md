# M66 verification report

Plan: docs/PAPER5_M66_verification_plan.md (commit c94cf9b, committed before any M66 run).
Campaign: 50 jobs, 14:48 to 20:39 on 2026-10-17, plus the follow-up diagnostics below.
Machine-readable results: experiments/results/m66_v1v2.json (V1/V2), experiments/results/m66_verify.json (V3/V4).

## V1 reproducibility (same seeds, fresh processes)

| Cell | Seeds | Result |
|---|---|---|
| Env B N=3 AXIOM v2 | 900-904 | identical (max diff 0) |
| Env B N=3 MAPPO | 900-904 | identical |
| Env B N=3 independent DQN | 900-902 | identical |
| Env B N=3 single-agent DQN | 900-902 | 901, 902 identical; 900 differs by 1.14 reward |
| Env B N=3 rule_static, rule_local (selection rerun) | 900-929 | identical |
| Env A N=3 AXIOM v2 | 900-904 | identical |
| Env A N=19 ring AXIOM v2 | 900-901 | identical |
| Env B N=7 ring AXIOM v2 MLP | 900-902 | identical |
| Env A federated sigma 0 | 900-901 | identical (results JSON and eval logs) |
| Env A disruption, AXIOM dropout | 900-909 | eval logs identical; summary floats differ in the 17th digit only |
| Env A rule_static vs stored oracle (extra check) | 900-929 | identical, so the oracle is the shed-every-mMTC rule |

### Single-agent DQN root cause

- The frozen framework's `run_mc` calls `build_policy` before `run_single` calls `set_seeds`. The initial Q-network weights therefore come from torch's default generator, and torch draws that generator's seed at random in every new process (`torch.initial_seed()` differs between processes).
- An instrumented wrapper, `experiments/scripts/m66_single_agent_seed_diag.py`, confirmed the cause. Two same-seed runs saw identical training batches but had different weights before the first update.
- Only the first seed run in each process is affected. Later seeds start from a torch state left by the earlier seeded run, so they reproduce, as seeds 901 and 902 did.
- A fixed `PYTHONHASHSEED` does not help. Five reruns of seed 900 gave 7.594, 7.598, 7.448, 8.647, and 9.668, against 8.735 stored.
- Sensitivity, dropping the first-of-batch seeds 900, 910, 920, and 1000:
  - Every single-agent comparison keeps its direction.
  - Env A N=3: AXIOM's lead goes from +0.311 (Holm p 0.066, n.s.) to +0.241 (Holm p 0.039, significant).
  - Env B N=3 stays at p < 1e-7.
- The manuscript already said, in the scaling section, that the single-agent DQN is not bit-reproducible, but it gave no cause or size. The plan wrongly assumed this was fully stated. The new subsection "Reproducibility and Fresh-Seed Verification" now gives both, and the scaling sentence points to it.

## V2 fresh seeds 3000+ (26 predictions stated in advance, all hold)

- Env A N=3, 20 seeds:
  - AXIOM reaches 98.2% of the oracle (12.607 vs 12.836).
  - It beats the independent DQN (+0.814, Holm p 0.0014) and MAPPO (+2.577, Holm p 0.0003).
  - Not predicted: AXIOM vs the single-agent DQN is −0.021, p 0.07, W/T/L 11/4/5. The pooled-40 lead does not carry over, and the paper now says so.
- Env A N=19 ring, 15 seeds:
  - AXIOM priority SLA is 95.6%; the independent DQN, single-agent DQN, and MAPPO reach 47.8%, 65.5%, and 61.2%.
  - All 6 tests are at Holm p ≤ 0.001.
  - Collapses: AXIOM 1, single-agent DQN 13.
- Env B N=3, 20 seeds:
  - AXIOM beats static (+2.562) and accept-all (+4.580) in 20/20 seeds.
  - It leads the independent DQN, single-agent DQN, and MAPPO at Holm p ≤ 0.0002.
  - rule_local beats AXIOM, 9.175 vs 8.782.
- Env B N=7 ring, 10 seeds:
  - rule_local beats every learned arm, p ≤ 0.004.
  - The MLP beats GAT AXIOM (−1.381 reward, p 0.006, 9/10 seeds). That is stronger than the main campaign's trend.
  - AXIOM vs static: +0.734, p 0.31, n.s.

## V3 independent recomputation

`m66_verify.py` passes 206 of 206 checks. These include checks of the new verification subsection and a self-check of the quoted count. All 24 quoted bootstrap CIs match.

The archived summary JSONs and figures fig6 and fig11 were regenerated with the order-independent bootstrap. Only CI fields changed: at most 0.026 in figure bars, and no point estimate or p-value moved.

## V4 integrity

- Evaluation streams (5000 + seed) are disjoint from every training and selection stream, including the fresh seeds.
- Replication seeds are disjoint from the primary seeds.
- Every evaluation log has 50 episodes.
- The DP epsilon values recompute.
- Live deployment:
  - 0 below-floor samples in 107,200 readings (m49b_2, m49b_3 gate reports).
  - Loss is 0 in every sample of m49b_1 result_full_3ue (7 samples) and result_full_6ue (12 samples).

## Housekeeping

- `run_cmd.sh` logs `exit=$?` after `$(date)`, so the logged exit codes are always 0. Completion was therefore verified by seed counts and by the absence of tracebacks.
- Disk reached 97% during the campaign. Space was recovered losslessly by gzipping the M66 logs and the unused m6_pilot training logs (24 GB). Nothing was deleted except the transient rule-selection logs, as the plan intended.

## M66b: further fresh seeds 3000-3009 (addendum 1), 8 of 11 criteria hold

Campaign: 21 jobs, 20:59 to 23:47 on 2026-10-17. Analysis in experiments/results/m66b_analysis.json.

- Env A N=19 hex: all 5 criteria hold.
  - AXIOM priority SLA is 96.5% (1 collapse in 10).
  - The independent DQN, single-agent DQN, and MAPPO reach 47.5%, 65.2%, and 63.0%.
  - All 6 tests are at Holm p ≤ 0.012.
- Federated sigma 0: holds. Centralised 12.389 vs federated 12.312, diff +0.077, CI [−1.03, 1.27], p 1.
- Env A N=7, ring and fully-connected: 3 criteria fail.
  - Holds: AXIOM pooled priority SLA is 96.7%, and AXIOM leads every baseline in all 12 comparisons by direction.
  - Holds: MAPPO pooled priority SLA is 68.1%.
  - Fails: the independent DQN reaches 80.9% and the single-agent DQN 80.6%, above the 80% bound. The main campaign had about 75-76%.
  - Fails: all 12 at Holm p < 0.05.
    - Ring: all 6 hold, Holm p ≤ 0.0313.
    - Fully-connected: none holds, Holm p 0.12 to 0.25. Two weak AXIOM seeds, 3006 at 57.2% and 3000 at 76.9%, leave the leads of 12.5 to 25.3 points non-significant on 10 seeds.
- No extra seeds were added after these results were seen. The failures are reported in the manuscript's verification subsection and in the conclusion.
- The verifier now has 224 checks, including every M66b number quoted in the text, and all pass. It caught two of my own drafting errors before commit: "p ≤ 0.031", where the true value is 0.03125, and "12.6", where it is 12.548.
- Pre-existing issue noticed: the abstract is 290 words, which is likely over the journal's limit.
