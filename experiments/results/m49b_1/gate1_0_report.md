# M49b-1-0 — GATE report: reuse audit for honest post-fix served-capacity anchors

## Status: NO RIG, analysis only, reading M44-A/C/D/E1/E1b/E2/E2b/E4's own already-committed reports and data. Verdict: 5 of 6 (slice x UE-count) cells are GAPs; 1 (embb/3UE) has a strong, directly reusable anchor with one stated caveat.

## Why M44's own data mostly does not transfer

Every M44 sub-report deliberately chose an ELEVATED per-slice load
(urllc 12x native, embb 3x native, mmtc 50x-320x native) specifically
to find each slice's graded shed band above the 5-PRB scheduler floor
— that was M44's own stated goal (GATE A onward), and it succeeded at
that goal. But M8's live single-gNB anchor and M27's topology
recalibration need something different: **honest served-capacity/demand
at the load M8 actually ran**, which is native per-slice traffic
composed by real UE COUNT (3UE = one UE per slice at its own native
rate; 6UE = two UEs per slice, not one UE at double the rate). These
are two different experimental designs, not the same thing measured
two ways — M44 never ran multiple simultaneous native-rate UEs on one
slice, and mostly never tested native load at all.

## Per-slice, per-UE-count result (full detail: `reuse_matrix.csv`)

| slice | 3UE (1x native) | 6UE (2x native) |
|---|---|---|
| urllc | **GAP** — only measured at 12x (M44-D); native only via the contaminated `avg_prbs_dl` artifact | **GAP** — never measured at any load between native and 12x |
| embb | **PARTIALLY REUSABLE** — M44-E2's own native-load fixed-ceiling sweep matches this load exactly (full health, 5-25 raw PRB, including at the floor) | **GAP (partial)** — an uncapped, single-slice demand reading exists (2x/8000Kbps, mean 16.6 PRB, not floor-contaminated) but no served-throughput sweep |
| mmtc | **GAP** — only measured at 50x+ (M44-E1/E1b); a strong prior for trivial full health exists but is unconfirmed, and native mmtc's real bursty (2s-on/6s-off) shape has never been exercised at all | **GAP** — same, plus never tested with 2 simultaneous UEs |

## What this means for M49b-1-1's scope

**5 of 6 cells need a new live probe.** The one partial exception
(embb/3UE) should be reused as-is per the matrix's own recommendation
— re-running it would spend live rig time confirming something already
cleanly established (full health at every ceiling down to the absolute
floor, at exactly this load), for a coupling effect M44-E4 itself found
is only material well above native load.

The new probes needed, in order of how well-understood the expected
outcome already is (informs how much rig time each deserves, not
whether to run it):

1. **mmtc at true native, 3UE and 6UE** — informed by a strong prior
   (E1's own 50x-floor result already shows near-full health), likely
   the fastest probe to run and confirm, but must use mmtc's real
   bursty traffic shape (2s-on/6s-off), not a continuous CBR stream
   like every prior M44 probe — this is genuinely new ground, not just
   a lower-multiplier repeat.
2. **embb at 2x native (6UE, 8000 Kbps)** — a short fixed-ceiling sweep
   reusing M44-E2's own script/protocol directly, extended above its
   existing ceiling grid since demand is known (from the already-valid
   uncapped reading) to sit around 16-17 raw PRB.
3. **urllc at native and 2x native (3UE and 6UE)** — the least
   characterized of the three: M44 has zero above-floor data at these
   loads for this slice, and unlike mmtc there is no strong prior from
   an adjacent already-measured point (M44-D's nearest data point,
   12x/3600Kbps, is a large multiplicative jump from 1x/300Kbps).

**All new probes should run the three slices SIMULTANEOUSLY, matching
M8's own composition** (M44-E4's co-location methodology, applied at
native/2x-native load instead of M44-E4's own elevated bands), with
real per-UE-count traffic (1 or 2 genuine `nr-uesoftmodem`/iperf3
client pairs per slice, not a single stream at a scaled rate) — not
run per-slice-in-isolation the way M44-D/E1/E2 did. This is a
methodological upgrade over M44's own convention, made necessary by
what M8/M27 actually need, not a criticism of M44's own (successful,
for its own different question) design.

## STOP

Per the milestone's own gating. Awaiting go before M49b-1-1 (the new
live probes named above).
