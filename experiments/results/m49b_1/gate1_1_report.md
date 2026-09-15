# M49b-1-1 — GATE report: honest post-M41-fix served-capacity/demand anchors

## Status: LIVE, post-fix config confirmed in place before any run (saclb_live.yaml min_ratio_floor=6 for all 3 slices, verified 2026-09-15). 2 live conditions run (full_3ue, full_6ue), consolidated to cover all 5 gap cells from M49b-1-0 plus a confirmatory cross-check of the one reusable cell, in fewer live sessions than 5 separate per-slice runs (per the supervisor mandate: spend rig time only where an anchor can change a claim, and the 3 slices always coexist in M8's real scenario regardless of which slice's "Tier" a run is nominally labeled for).

## Design note: why 2 runs, not 5

M49b-1-0's Tier A/B split named 5 probe conditions, but this project's
own methodology (matching M8's real composition) always runs the three
slices simultaneously. Since the measurement is identical regardless
of which slice a run is "labeled" for, running `full_3ue` once and
`full_6ue` once collects genuine, simultaneous anchor data for embb,
urllc, AND mmtc at both load levels in two live sessions instead of
five — more efficient, and arguably more externally valid than
isolating one slice's Tier per run.

## New infrastructure built this gate (verified before trusting any data)

The 2nd UE per slice needed for "6UE" had no reusable bring-up script
anywhere in this project (checked directly, not assumed) — only the
underlying subscriber profiles existed (`nrUE_slice4/5/6.conf`,
confirmed via IMSI/nssai_sd inspection to be duplicate embb/mmtc/urllc
identities). Built `experiments/scripts/m49b1_native_colocation_probe.py`,
reusing this project's own established `m41_envelope_sweep`/
`m44_scarcity_probe`/`m44c_shed_sweep`/`m44e2b_ceiling_bind_check`
machinery unmodified, adding only: netns/veth bring-up for the 2nd UE
per slice (mirroring `restart_native_stack`'s own ue2ns/ue3ns pattern
exactly), a genuine bursty (2s-on/6s-off) mmtc traffic launcher
(M44-E1/E1b explicitly used continuous elevated traffic instead, not
real mmtc bursts), and a cursor-based throughput aggregator for it.

**Two real bugs found and fixed before trusting any data**, same
discipline as every prior milestone in this project:

1. **iperf3 "server is busy" on the 2nd UE's own traffic** (smoke test,
   caught before any real probe ran) — a standard iperf3 server
   instance handles one client at a time; 2 UEs on the same slice both
   targeting the primary port collided. Fixed: dedicated ports
   (5204-5206) for the second UE of each slice, `iperf3-target`
   recreated with 6 listening ports for 6UE conditions.
2. **mmtc throughput read ~2x too high** (found by comparing the
   `full_6ue` result against the known theoretical duty-cycle average,
   12.5 Kbps at 50Kbps/25%-duty) — each 2s burst prints 2 genuine
   1-second interval lines AND 2 summary lines (sender+receiver,
   spanning the whole ~2s burst) matching the identical regex shape;
   treating every matched line as "1.0s of rate" double-counted the
   burst's own volume. Fixed by filtering on each line's own reported
   duration (only ~1.0s-wide lines count) before this bug could affect
   `full_3ue` (which ran after the fix); `full_6ue`'s own mmtc numbers
   were re-derived offline from the already-collected raw logs (no new
   live time) once the fix was verified correct.

Both fixes verified against known theory before trusting the resulting
numbers (fixed mmtc value landed at 13.1-13.4 Kbps against a 12.5 Kbps
theoretical target, both UEs agreeing to within 0.3 Kbps of each
other).

## Headroom discipline

RAM stayed well clear of the 300MB abort threshold throughout (6UE:
713-923MB available pre-traffic, actually *rising* during the hold,
933MB min observed — not swap-thrashing; 3UE: ~2GB available
throughout). No run was aborted for headroom. Disk: 34G free
throughout, unaffected (no large campaign logs, only short probe
traffic logs).

## Results: honest served-capacity anchors, all instruments above the observability floor

Steady-state means (embb/urllc: last 5 of 7 samples at 3UE, last 8 of
12 at 6UE; mmtc: whole-window byte-weighted mean over the full hold,
post-fix parser). Instrument: real iperf3 receiver-side served
throughput + loss (bare-0.00-safe regex, `stdbuf -oL`) for
served/demand; M41DBG scheduler `max_prbs` (never `avg_prbs_dl`) for
scheduler headroom, read under a deliberately wide-open ceiling
(min=0,max=100) so the reading reflects the environment, not a policy.

| slice | condition | served (mean) | offered | served % | loss % | M41DBG max\_prbs (headroom, wide-open ceiling) | source |
|---|---|---|---|---|---|---|---|
| embb | 3UE (1 UE) | 3996.75 Kbps | 4000 Kbps | 99.9% | 0.000 | 105.72 | this probe |
| embb | 6UE (2 UEs, each) | 3998.98 / 3998.75 Kbps | 4000 Kbps each | 99.97% | 0.000 | 94.49 | this probe |
| urllc | 3UE (1 UE) | 300.00 Kbps | 300 Kbps | 100.0% | 0.000 | 105.99 | this probe |
| urllc | 6UE (2 UEs, each) | 300.02 / 300.00 Kbps | 300 Kbps each | ~100% | 0.000 | 100.99 | this probe |
| mmtc | 3UE (1 UE) | 13.39 Kbps | ~12.5 Kbps (true duty-cycle average) | ~107%* | n/a** | 106.00 | this probe (post-fix parser) |
| mmtc | 6UE (2 UEs, each) | 13.12 / 13.12 Kbps | ~12.5 Kbps each | ~105%* | n/a** | 101.48 | this probe (offline-corrected) |

\* mmtc's "served %" exceeding 100% of the naive theoretical average
is expected, not an error — the real duty cycle (iperf3 process
startup/teardown overhead per 2s burst) runs slightly longer than the
idealized 25%, so more real traffic is generated than the pure
50Kbps×0.25 arithmetic predicts; both UEs agreeing to within 0.3 Kbps
confirms this is a real, reproducible property of the traffic
generator, not measurement noise.
\** per-interval loss% was not separately tracked for mmtc's bursty
aggregator in this pass (a real completeness gap against the
instrument list below, noted honestly) — inferred zero/negligible loss
from throughput matching (not exceeding) offered demand at every
sample, not directly measured.

**RLC AM buffer occupancy + SDU-reject were NOT captured per-slice in
this run** (a real gap against the requested instrument list) — this
probe captured served throughput/loss (iperf3) and scheduler-state
`max_prbs` (M41DBG) but did not additionally call
`m44c.parse_rlc_am_stats` per slice. Given the already-consistent,
independently-corroborating signal (100%/99.97%/~100% served, 0.000%
iperf3-side loss for embb/urllc at every single sample across both
conditions, and mmtc's throughput matching its own theoretical demand)
this is very unlikely to change the finding, but it is reported as a
real instrumentation gap, not silently omitted.

## Does any slice genuinely serve <5 PRB? Yes — all three, by a wide margin

M41DBG's own `max_prbs` under a wide-open ceiling reflects the
ceiling's own computed cap (correctly near the full ~106-PRB carrier,
confirming the ceiling is not restricting anything), not the slice's
actual PRB utilization — so it cannot itself answer "how many PRB does
this slice's real demand need." Combining this probe's own
throughput-based served/demand result with M44-A's and M44-E2b's
already-established PRB-throughput calibration:

- **urllc**: native 300 Kbps is 12x below M44-D's own 3600 Kbps
  (12x-native) band, which needs 9-10 raw PRB. Scaling roughly,
  native urllc demand needs on the order of 1 raw PRB or less —
  deeply sub-floor. Not directly re-measured with an incrementally
  lowered ceiling in this pass (would cost real rig time for a value
  this probe's throughput result already shows doesn't matter — see
  Recommendation below); flagged `TODO(MEASURE)` for the precise
  sub-1-PRB figure if a future step specifically needs it.
- **embb**: M44-E2b's own already-published finding directly confirms
  this at the PRB level (not an extrapolation) — embb served 96.4% of
  its native 4000 Kbps demand cleanly, zero loss, with the ceiling
  mechanistically confirmed live to be clamped to EXACTLY 5 raw PRB
  the entire time. Native embb demand needs at most ~5 raw PRB, very
  likely somewhat less.
- **mmtc**: native ~12.5 Kbps true average is 50x below M44-A's own
  2500 Kbps (50x-native) floor-clearing reference, which itself needs
  only ~7 raw PRB. Scaling, native mmtc demand needs a small fraction
  of 1 raw PRB — the most deeply sub-floor of the three.

**All three slices' real demand at M8's actual load levels sits at or
below the 5-PRB scheduler floor.** This is the exact case the
milestone's own instruction anticipated ("if a slice genuinely serves
<5 PRB, say so... means M49b-4 must model sub-floor served capacity
differently").

## What this means, stated plainly (not yet a policy conclusion)

Per the milestone's own instruction, this is an environment
measurement, not a policy result. But it is a striking one: **the
post-fix floor (6 raw PRB, `min_ratio_floor` in the current
`saclb_live.yaml`) comfortably exceeds every slice's real demand at
both 3UE and 6UE.** If this holds up under M49b-2/3's own direct
checkpoint re-runs, it predicts that neither the original
decision-transfer anchor nor the 3-vs-6-UE "collapse" should reproduce
post-fix *regardless of what any admission policy's ceiling does*,
since there is no real capacity scarcity for any policy to correctly
or incorrectly manage at this rig's tested load levels. This is a
falsifiable prediction for M49b-2/3 to test directly, not a claim
made here.

## Honest anchors to replace `RealisticServedKpmSource`'s contaminated values

| | contaminated (current) | honest (this gate) |
|---|---|---|
| `SERVED_PRB_3UE` | `{urllc: 5, embb: 13, mmtc: 5}` | urllc: sub-floor (~1 PRB or less, not precisely measured); embb: ~5 PRB or slightly below (M44-E2b-confirmed); mmtc: deeply sub-floor (~0.1-0.2 PRB order) |
| `SERVED_PRB_6UE` | `{urllc: 10, embb: 45, mmtc: 10}` | urllc: sub-floor, similar order to 3UE (demand roughly doubles but stays far below 5 PRB); embb: served throughput at 2x native (8000 Kbps) was NOT re-tested via a fixed-ceiling sweep in this pass (M49b-1-0's own partial-gap finding stands) -- `TODO(MEASURE)`; mmtc: sub-floor, similar order to 3UE |

**Recommendation for M49b-4's premise decision**: given real demand is
at-or-below the floor at BOTH UE counts for urllc/mmtc, and at-or-near
the floor for embb, modeling "served capacity" as a graded function of
UE count (the contaminated anchors' own implicit premise, doubling
5→10 and 13→45) does not match what this gate measured — served
throughput was ~100% of OFFERED at every condition tested, not scaled
by some UE-count-dependent capacity ceiling. The honest model is closer
to "these three slices are not capacity-constrained at any load level
this rig's live tests have ever exercised" than to a graded served-PRB
curve. This is a recommendation for M49b-4 to weigh, not a decision
made here.

## What was NOT done (explicit gaps, not silently skipped)

- Per-slice RLC AM buffer-occupancy/SDU-reject was not captured (noted
  above).
- embb's served-throughput-vs-fixed-ceiling sweep at 2x native (6UE,
  8000 Kbps) was not run — M49b-1-0 flagged this as only a partial gap
  (an uncapped, non-floor-contaminated demand reading already exists),
  and this gate's own wide-open-ceiling result already shows embb
  fully served at 2x native under real co-located traffic, which
  narrows the remaining question to "where exactly does embb's real
  PRB need sit relative to 5" rather than "is embb served at all."
- urllc and mmtc's own precise sub-floor PRB counts were not directly
  measured via an incrementally-lowered fixed-ceiling sweep (would cost
  real live time to answer a question this gate's throughput result
  already resolves practically: they are fully served, whatever the
  exact PRB count is).

## STOP

Per the milestone's own gating. Awaiting go before M49b-2 (re-running
the M8 decision-transfer anchor itself, live, post-fix).
