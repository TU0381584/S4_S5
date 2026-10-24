# M77: throughput and backlog-delay measurements (descriptive plan)

Committed on 2026-10-24, before any M77 run. A comparison with 50 comparable 2025-2026 journal papers found that most report throughput or latency, which this manuscript does not. The evaluation logs do not record served PRBs or backlog, so M77 re-runs the usual evaluation of stored checkpoints and rules with a recorder on the simulator's per-step UE samples (experiments/scripts/m77_kpi.py). Every run is checked against its stored evaluation log (reward, blocks, SLA); a run that does not reproduce is reported and excluded. Nothing is retrained, and no hypothesis is tested: the measurements are descriptive.

## Metrics, per slice, averaged over steps, gNBs and seeds
- Throughput: PRBs served per gNB per step, and served over offered demand.
- Backlog: unserved PRBs carried per gNB per step.
- Delay proxy: mean backlog over mean served PRBs, a queueing delay in control periods (5 s each) from this fluid model, not packet latency. Tail: the 95th percentile over steps and gNBs of backlog over served.

## Cells and arms
- Env A, 3 gNBs (m65_n3_view, seeds 900-929) and 37 gNBs hex (m73/A_n37_hex, seeds 900-926, 1000-1002): AXIOM, single-agent DQN, independent DQN, MAPPO, static rule, accept-all.
- Env B, 3 gNBs (m64/n3_fully_connected, seeds 900-929) and 19 gNBs hex (m75/D_envB_n19_hex, seeds 900-911, 1000-1002): the same learned arms, static rule, accept-all, and the tuned local rule (selected in the cell at 3 gNBs, carried over from seven gNBs at 19).
