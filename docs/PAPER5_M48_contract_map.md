# M48 — contract map: Paper #3's promises vs. what Paper #5 delivers

Source for every "#3" claim below: the published paper itself
(`/home/kmanojp/Desktop/Comprehensive_Review_of_Optimization_Techniques_for_User-Centric_Distributed_Network_Slicing_in_5G_Networks.pdf`,
bib key `ref:access`/`survey-paper3`, IEEE Access vol. 14, pp.
114630-114648, 2026), read directly (Table 12, Table 10, Section VII,
the Conclusion) rather than recalled from memory. Source for every
"#4" claim: `Papers_4-5/Paper_4/main.tex`, read directly.

## 1. Table 12 (Implementation specification of the proposed GAT-MARL-FL framework) → Paper #5 sections

| #3 Table 12 component | Input → Output → Location (as specified) | Implementation target (as specified) | Paper #5 section that delivers it | Status |
|---|---|---|---|---|
| QoE mapper | RAN KPIs → inferred MOS/QoE class → MEC/Near-RT RIC | Temporal NN tuned on objective MOS + ACR labels | **Not yet in the manuscript.** M53 (QoE-reward arm) is the first place a QoE mapper enters this codebase's multi-gNB line — Paper #4 already has one (single-gNB, its eq. 3-5), reused as the calibrated coefficient source per M53's own spec. | Pending M53 |
| GAT encoder | gNB-MEC graph (node/edge features) → topology-aware embedding → Near-RT RIC | 3 GAT layers, 64 hidden dims, 4 attention heads | GAT encoder + CTDE (M2), Cluster-Size Scaling (M6/M27) | **Delivered, at a smaller spec** (2 layers, 16 hidden, 4 heads — matches on heads only). M51 is the pending reconciliation: run the #3-spec encoder and check whether the headline results hold, and whether the smaller encoder is a measured, justified choice for these graph sizes rather than an unexamined deviation. |
| MARL controller | QoE/resource state, slice demand → AC/RA/RO actions → Near-RT RIC xApps | CTDE with decentralised local execution | GAT encoder + CTDE (M2), all multi-gNB sections | **Delivered** — Algorithm 1 in the current manuscript is exactly this (centralised training via the shared encoder's joint loss, decentralised execution via each agent consuming only its own embedding row). Scope is narrower than "AC/RA/RO": admission control (accept/reject a pending request) only, not resource allocation or orchestration — stated as the deliberate scope in System Model, not hidden. |
| FL coordinator | Local model updates → global QoE/policy model → Non-RT RIC/MEC | FedAvg-FedProx to limit client drift/stragglers | FL coordinator (M3/M7) | **Delivered**, including the FedProx null result (M7) — a real, measured finding (no dividend at any tested strength) rather than an assumed benefit, which #3 itself only proposes, not validates. |
| Privacy layer | Local gradients/updates → clipped/noisy update → MEC/Non-RT RIC | Differential privacy before aggregation | Privacy layer (M3), formal zCDP bound | **Delivered** — DP-SGD clip+noise exactly as specified, plus a formal (ε,δ) bound #3 does not itself compute. |

**Net**: 4 of 5 Table 12 components are delivered and measured; the QoE
mapper is the one component #5 has not yet implemented at the
multi-gNB level, and M53 is scoped specifically to close that gap.

## 2. Section VII directions 2/3/5 → Paper #5 results

#3's own Section VII ("Future Work") lists five validation directions
before any deployment-level claim. Directions 1 and 4 (calibrating
inferred MOS against objective/ACR labels; O-RAN execution on
validated/reproducible testbeds via xApp/rApp loops) are addressed
partially by Paper #4 (single-gNB xApp/E2 loop, live) and not yet by
#5's multi-gNB line — flagged in the promises-not-honoured list below,
not claimed here. Directions 2/3/5, which #5 does address:

| #3 direction (verbatim intent) | Paper #5 result | Section |
|---|---|---|
| **2. Topology scalability** should be tested under dynamic gNB/MEC traffic, handovers, varying slice densities | N=3→7→19 scaling under 3 adjacency structures (fully-connected/ring/hex), collapse-resistance converging to 35.4% [25.5%,45.8%] over 3 independent samples/64 seeds, then re-validated under a measured-anchor-recalibrated simulator (M27) | Cluster-Size Scaling (§results-m6, §results-m27) |
| **3. FL/privacy overhead** should be quantified via model-update latency, communication cost, privacy noise, utility loss | Federation reward cost (n.s., +0.133), DP block-precision threshold (real, at σ>1.0, not smooth), zCDP formal bound, FedProx drift measured directly (0.03%-1.44% of TD loss) | FL coordinator (§results-m3), pending: M51's latency/sync-time measurements against #3's own numeric targets |
| **5. Resilience** should be stress-tested under disruption recovery, straggler clients, delayed synchronisation, resource scarcity | gNB dropout, demand spike, agent churn, evaluated on frozen checkpoints with accelerating severity cost found for every arm; one architectural overclaim (independent-DQN churn immunity) caught and retracted via independent-seed replication | Disruption Resilience (§results-m4) |

## 3. #3's five deployment constraints → Paper #5 measurements

Quoted from #3 Section VII ("Five practical deployment constraints
also remain") and the constraints paragraph immediately preceding it
("For deployment, the target constraints are MEC inference latency
below 5 ms, synchronisation latency below 10 ms, and model pruning to
below 10% of the original model size").

| #3 constraint | Measured by #5? | Where |
|---|---|---|
| Non-IID traffic across cells can degrade MARL generalisation / FL convergence | **Partially.** M7 found genuine per-gNB load heterogeneity (an "implicit, seeded per-gNB load multiplier" the cluster-scaling work revealed) and swept FedProx against it — the mitigation earns no measurable dividend, but heterogeneity's raw cost on MARL generalisation itself (not just FedProx's ability to fix it) is not separately isolated. | FL coordinator (§results-m3) |
| FL communication overhead may exceed constrained gNBs' backhaul | **Not yet measured** — no communication-cost/bandwidth number is reported anywhere in the current manuscript, only reward/precision cost. | Pending M51 |
| DP trades inference accuracy for protection, calibration is deployment-specific | **Delivered** — the σ-sweep is exactly this trade-off, with the real (not smooth) threshold and the compliance-metric masking of it as a second, independent instance of the paper's own central finding. | Privacy layer (§results-m3) |
| Near-RT/Non-RT RIC layers impose strict latency budgets (<10ms / <1s) bounding GNN+MARL complexity per control cycle | **Not yet measured** at the multi-gNB level — Paper #4 measured the single-gNB E2 round trip (0.57ms median) and DQN inference (67.9-68.3µs), but GAT-CTDE's own per-step inference latency at N=3/7/19 has never been timed. | Pending M51 (the CONTEXT block's own <5ms per-step target) |
| Real-time QoE inference needs pruning + edge-local inference to meet the sub-5ms target | **Not yet measured** — no QoE mapper exists at the multi-gNB level yet (see Table 12 row above), so nothing to time or prune. Paper #4's own single-gNB QoE-mapper LSTM already misses this exact target (~7.3ms observed vs 5ms), a concrete, already-measured warning sign to carry into M53/M51 rather than assume away. | Pending M53 (build) then M51 (measure) |

**Net**: 1 of 5 deployment constraints is fully measured (DP), 1 is
partially measured (non-IID/heterogeneity), 3 are entirely open —
communication overhead, RIC-layer latency budgets, and QoE-pipeline
timing/pruning. M51 is scoped directly at closing the two latency
gaps; the communication-overhead gap is not currently scoped by any
named milestone and should be flagged to the user rather than silently
left for M51 to absorb without being asked.

## 4. Paper #4's four open/future-work items → where #5 answers each

Quoted directly from Paper #4's Conclusion and Future Work section.

| #4 open item (verbatim) | #5 answer | Section | Status |
|---|---|---|---|
| "the closed-loop simulator's backlog-capacity parameter needs validating against measured live SLA-margin magnitude rather than offered-load levels alone" | M1's own attempt (backlog_capacity/drift/AR1 grid search) is a **negative result** (rho=0.097 unchanged) — the fix that actually worked is a different mechanism entirely: M8/M27's `RealisticServedKpmSource`, anchoring served PRB directly to real 3-UE/6-UE measurements via a mean-reverting interpolation, validated by reversing a complete live collapse | Live Single-gNB Anchor (§results-m8, §results-m8-fix), Cluster-Size Scaling (§results-m27) | **Answered**, but by a different mechanism than #4 itself named — worth stating explicitly in M54's Introduction so the connection reads as delivered, not coincidental |
| "extend this deployment toward the fully-fledged GAT-MARL-FL framework" | GAT-CTDE, extended to N=19, federated, DP-private | GAT encoder + CTDE, Cluster-Size Scaling, FL coordinator | **Answered** (offline-only; see the multi-gNB-live gap below) |
| "whether the E2 interface's per-slice ceiling primitive still suffices once a graph-attention policy coordinates multiple gNBs" | **Not answered.** This is specifically a live-multi-gNB question; #5's entire GAT-CTDE line is offline-only (System Model states this explicitly). M28's live 2-gNB attempt found a real hardware ceiling before this question could even be approached. | Limitations | **Open**, stated as a limit, not answered |
| "whether the negligible control-loop overhead measured here holds once coordination and federated aggregation run on top of it" | **Not answered** for the same reason, and also not yet measured *offline* either (see deployment-constraints table above — GAT-CTDE per-step latency has never been timed, live or offline). | Limitations / Deployment Targets (pending M51) | **Open** — M51 can close the offline half of this; the live half is blocked on the same live-multi-gNB gap |

## 5. #3 promises Paper #5 cannot honour — stated for the Limitations section, not hidden

1. **Multi-gNB LIVE deployment.** #3's own framework is explicitly for
   live O-RAN execution (Table 12's every "Location" column names a
   real RIC layer). Every multi-gNB result in #5 — GAT-CTDE, FL, DP,
   disruption, all of cluster-size scaling — is offline-simulation
   only. This is not a soft caveat: M28's own live 2-gNB attempt found
   a genuine hardware ceiling on this exact rig (simultaneous
   registration across 2 gNBs works; two complete live RF links under
   real sustained traffic at once does not, and CPU-affinity isolation
   ruled out a fixable host-scheduling cause). The current manuscript
   already states this limit in its Conclusion; M54 should keep it,
   sourced to `docs/PAPER5_M27_M28_scope.md` rather than left as an
   unsupported assertion.
2. **MEC-host nodes in the graph.** #3's Table 12/Fig. 4 explicitly
   defines the graph as `V = {gNBs, MEC hosts}`. #5's `topology.py`
   builds an adjacency over gNBs only — no MEC-host node type exists
   anywhere in this codebase's graph construction. This has never been
   stated as a limitation anywhere in the current manuscript and should
   be added, not left implicit.
3. **Near-RT/Non-RT RIC layering.** #3 specifies its MARL controller
   living inside "Near-RT RIC xApps" specifically, with a separate
   Non-RT RIC layer for FL coordination, each carrying its own latency
   budget. Paper #4's actual live testbed (which #5's single-gNB anchor
   reuses) runs a "RIC-free E2 agent (UDP loop)" by its own explicit
   description — a deliberate simplification, not an oversight, but one
   #5 has also never stated plainly. Minor relative to items 1-2 (the
   xApp/orchestrator concept is present even without full RIC
   layering), but still a real, statable gap.
4. **Real (not synthetic) cross-organisation privacy setting.** Already
   stated as a limit in the current manuscript's Conclusion (§2) — kept
   here for completeness, not new.

## 6. What the current manuscript already gets wrong relative to the binding citation rule

The **existing** WPC manuscript, before any M48-M54 edit, cites Paper
#4's headline compliance finding in a way M43 has since undermined:
Introduction ("showing its compliance advantage survives correction
for multiple comparisons") and §results-m27's closing paragraph
("a QoE-aware reward's compliance advantage surviving correction for
multiple comparisons"). Per the binding citation rule for this
overhaul, and per M43-P0/P1/P1B's own findings (the compliance metric
is structurally blind to DL starvation; the actual submitted
config/checkpoint fails catastrophically under live reproduction; the
sub-floor condition is deterministic across all 28 submitted seeds),
**both of these citations need rewriting in M54** to cite only what
the rule permits: live E2 loop feasibility (0.57ms, <20K params), the
ceiling-not-accept/reject control-surface finding, offline/live
non-correlation, and the MOS pilot — not the 100%-compliance headline
as an established result. Flagged here so M54 does not silently
inherit text written before this session's own citation rule existed.

## STOP

Reported per M48's own gate. Awaiting review of the scope map, this
contract map, `docs/PAPER5_M48_novelty_statement.md`, and the
promises-not-honourable list above before any editing begins.
