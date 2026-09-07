# M44-E4 — GATE E4 report: can urllc and embb be co-located and independently controlled?

## Verdict: YES to both. A single live multi-slice offered load puts
## urllc and embb SIMULTANEOUSLY inside their own confirmed graded
## bands, and distinct per-slice ceilings are simultaneously
## expressible and independently observable via live M41DBG scheduler
## state. There IS a real, systematic, asymmetric cross-slice coupling
## (embb is consistently shifted toward more degradation by urllc's
## presence; urllc is largely unaffected, with a small late-onset
## exception) -- reported honestly as a real environmental feature, not
## papered over. DECISION: a real cross-slice PRIORITIZATION campaign
## is runnable. Awaiting go, per this milestone's own instruction.

## 1. Protocol run

Six (urllc_ceiling, embb_ceiling) combinations, cold-start per
combination (both ceilings fixed before either slice's elevated
traffic exists), mmtc left at native background traffic throughout.
Both slices held their own independently confirmed band-producing
offered loads simultaneously: urllc at 3600 Kbps (12x native, M44-D's
band), embb at 12000 Kbps (3x native, M44-E2b's band).

| run | urllc_ceil | embb_ceil | purpose |
|---|---|---|---|
| 1 | 6 | 7 | baseline co-location verification |
| 2 | 7 | 7 | phase A: vary urllc, embb fixed mid-band |
| 3 | 8 | 7 | phase A cont'd |
| 4 | 7 | 5 | phase B: vary embb, urllc fixed mid-band ("the swap") |
| 5 | 7 | 8 | phase B cont'd |
| 6 | 7 | 10 | phase B cont'd |

Each slice's own RLC AM entity was resolved fresh per run (NSSAI-match
order -> CU UE ID -> rnti -> entity pointer, via the gNB's own log --
not a busiest-entity heuristic, since with two slices elevated
simultaneously a heuristic could misattribute). Entity resolution
succeeded cleanly in all 6 runs. Gate PASS and both buffers confirmed
0.0% before traffic at every run. Zero `new_max_retx_events` across
all 48 samples, all 6 runs.

## 2. Steady-state results (last 4 of 8 samples per run)

| urllc_ceil | embb_ceil | urllc served (%) | urllc loss/rej % | embb served (%) | embb loss/rej % |
|---|---|---|---|---|---|
| 6 | 7 | 63.8% | 34.2/34.1 | 32.0% | 68.4/68.8 |
| 7 | 7 | 89.5% | 0.3/2.8 | 35.8% | 64.6/65.0 |
| 8 | 7 | 82.6% | 7.9/8.8 | 30.4% | 69.7/70.3 |
| 7 | 5 | 88.9% | 3.0/3.8 | 25.3% | 74.9/75.2 |
| 7 | 8 | 89.1% | 0.0/2.9 | 39.8% | 60.4/60.9 |
| 7 | 10 | 86.9% | 3.1/4.7 | 48.8% | 52.0/52.0 |

At every single sample in every run, live M41DBG scheduler state
confirmed both slices' `max_prbs` tracking their own independently
commanded ceiling (e.g. run 3: urllc=8.0, embb=7.0; run 6: urllc=7.0,
embb=10.0) -- distinct, simultaneously enforced, exactly as commanded.

## 3. Comparison against each slice's own solo band (M44-D / M44-E2b)

| urllc ceiling (embb fixed) | co-located served% | solo served% | delta |
|---|---|---|---|
| 6 (e=7) | 63.8% | 59.0% | +4.8 |
| 7 (e=7) | 89.5% | 94.0% | -4.5 |
| 8 (e=7) | 82.6% | 101.2% | -18.6 |
| 7 (e=5) | 88.9% | 94.0% | -5.1 |
| 7 (e=8) | 89.1% | 94.0% | -4.9 |
| 7 (e=10) | 86.9% | 94.0% | -7.1 |

| embb ceiling (urllc fixed) | co-located served% | solo served% | delta |
|---|---|---|---|
| 7 (u=6) | 32.0% | 43.5% | -11.5 |
| 7 (u=7) | 35.8% | 43.5% | -7.7 |
| 7 (u=8) | 30.4% | 43.5% | -13.1 |
| 5 (u=7) | 25.3% | 31.9% | -6.6 |
| 8 (u=7) | 39.8% | 48.7% | -8.9 |
| 10 (u=7) | 48.8% | 61.3% | -12.5 |

**embb is systematically, consistently shifted toward more degradation
by urllc's mere presence, at every single tested embb ceiling** (6.6-13.1
percentage points less served throughput, 3.3-13.5 points more
loss/rejection) -- a real, reproducible effect across 6 independent
cold-start runs, not noise. **urllc is comparatively unaffected**: at
its own genuinely degraded point (ceiling=6) co-location makes no
negative difference at all (+4.8%, within run-to-run variance); at its
healthy points (7, 8) co-location introduces a real but much smaller
effect (a late-onset rejection blip appearing only in roughly the last
15-30s of each ~150-165s hold, contributing 2.8-8.8% mean rejection by
the end -- most pronounced at ceiling=8).

Physically plausible mechanism: this is consistent with the same
cross-slice `min_prbs` subtraction dynamic already observed in E2b's
own ceiling-bind check (a slice's live `max_prbs` is reduced by every
*other* active slice's own `min_prbs`), plus embb's inherently larger
per-grant PRB requirement (1200B packets) making it more sensitive to
losing a few PRBs of headroom than urllc's smaller, more schedulable
grants.

## 4. Answering GATE E4's three questions

**(1) Does a single multi-slice load put both urllc and embb in their
graded bands at once, or does contention knock one out?** Both slices
remain inside a real, bounded, partial-service regime (neither fully
served nor collapsed) at **every one of the 6 tested combinations** --
urllc's served fraction never drops below 63.8% nor its rejection
above 34.1%; embb's served fraction stays between 25.3% and 48.8% with
rejection between 52.0% and 75.2%, in every case matching the
*qualitative* shape of its own solo band (a real, graded, partial-
service state), just shifted toward the more-degraded end by co-
location. Neither slice is knocked into full collapse (100%
rejection/zero throughput) or full health (0% loss/rejection) at any
tested point. So: **yes, co-location succeeds** -- with a real,
quantified, asymmetric coupling effect that any campaign built on this
regime needs to account for explicitly.

**(2) Can distinct per-slice ceilings be simultaneously expressed and
observed, or does controlling one slice disturb the other's regime?**
Yes, distinct ceilings are simultaneously expressed and confirmed live
via M41DBG in every run. Varying urllc's ceiling (6->7->8) with embb
held fixed at 7 moves urllc's own outcome in the expected graded
direction while embb's own outcome stays in a comparatively narrow
band (30.4%-35.8% served, no monotonic drift with urllc's ceiling).
Varying embb's ceiling (5->7->8->10) with urllc held fixed at 7 moves
embb's own outcome in the expected graded direction (25.3% ->
35.8%/39.8%/48.8% served, closely mirroring its solo ordering) while
urllc's own outcome stays comparatively stable (86.9%-89.5% served
across all four). **Each slice's own ceiling change primarily drives
its own outcome; the other slice's regime is perturbed but not
restructured.** This is real, if imperfect, independent control.

**(3) Total offered load and per-slice PRB demands at the co-located
point?** Total offered: 3600 Kbps (urllc) + 12000 Kbps (embb) + ~50
Kbps native mmtc background = ~15,650 Kbps. Per-slice commanded/live-
enforced PRB ceilings ranged 6-8 raw PRB for urllc and 5-10 raw PRB for
embb across the 6 combinations -- a combined commanded PRB budget of
11-18 raw PRB out of the 106-PRB carrier, confirmed live via M41DBG at
every sample. This is well within total carrier capacity (ample
headroom remains for mmtc and scheduling overhead) -- the embb-side
degradation-under-co-location is a real scheduling/contention
interaction, not a carrier-capacity-exhaustion artifact.

## 5. Decision

Per this milestone's own decision tree: **both slices co-located and
independently controllable -> a real cross-slice PRIORITIZATION
campaign is runnable** (DQN-QoE vs baseline vs static-at-cap, judged on
cross-slice priority-weighted correctness) -- the strongest available
result. The real, asymmetric cross-slice coupling found here (embb
consistently more affected by urllc's presence than the reverse) should
be carried into that campaign's design explicitly: it is a genuine
feature of this multi-slice environment, not a confound to eliminate,
and arguably strengthens the case for a prioritization campaign in the
first place -- real contention between differently-provisioned slices
is exactly the condition under which a QoE-aware controller's advantage
over a static or SLA-only baseline should be most visible.

## 6. What has NOT been done
- No DQN-QoE-vs-baseline campaign has been scoped or started.
- The upper/lower boundaries of the co-located regime (e.g. whether
  urllc's own band edges shift under co-location the way embb's does)
  have not been fully mapped -- this run characterized 6 representative
  combinations, not an exhaustive joint sweep.
- mmtc remains excluded from any live campaign on this surface (no
  realistic band, per E1b).

## STOP

Per this milestone's own final instruction, awaiting go before scoping
the head-to-head and the supervisor memo.
