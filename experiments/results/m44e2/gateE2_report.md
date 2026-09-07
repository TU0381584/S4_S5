# M44-E2 — GATE E2 report: embb cold-start graded-band characterization

## Verdict: NO shed band found for embb anywhere in the tested range
## (5-25 raw PRB) at its NATIVE load -- even the absolute 5-PRB scheduler
## floor serves ~96% of offered throughput with ZERO loss and ZERO RLC
## rejection. This contradicts the milestone's own working assumption
## that embb (like urllc) would show a confirmed band; the honest
## result is that embb's realistic-load controllability is UNRESOLVED,
## not confirmed. Await go, as instructed.

## 1. Phase 1: embb's demand-vs-load ramp at wide-open ceiling

M44-A never characterized embb (excluded as "clears the floor
natively"), so this is the first real per-UE avg_prbs_dl measurement of
embb across a load ramp, using the same method M44-A used for
urllc/mmtc. Multipliers of embb's own native rate (4Mbps/1200B
sustained):

| mult | offered | target rnti mean PRB | max PRB |
|---|---|---|---|
| 1x (native) | 4000 Kbps | 17.27 | 23.0 |
| 1.5x | 6000 Kbps | 15.00 | 18.0 |
| 2x | 8000 Kbps | 16.60 | 21.0 |
| 3x | 12000 Kbps | 21.07 | 34.0 |
| 4x | 16000 Kbps | 26.40 | 37.0 |
| 5x | 20000 Kbps | 30.33 | 37.0 |
| 6x | 24000 Kbps | 37.47 | 43.0 |
| 8x | 32000 Kbps | 56.13 | 70.0 |
| 10x | 40000 Kbps | 82.33 | 99.0 (near the 106-PRB carrier limit) |

Striking finding: at NATIVE embb traffic -- no elevation of any kind,
the most realistic possible load -- wide-open uncapped demand is
already mean=17.27 PRB (max=23), noticeably higher than urllc's own
reference point (mean=10.20, max=13.00) despite embb needing no
elevation at all to get there. embb is confirmed the highest-demand
slice, exactly as this milestone anticipated. (Some non-monotonicity
between 1x/1.5x/2x, similar noise to what was observed near mmtc's own
transition zone in E1b, not investigated further -- doesn't change the
overall shape.)

Given native (1x) demand already sits well within a testable range, and
per this milestone's own instruction that "sustained high-throughput IS
eMBB's nature" (unlike mmtc, elevating embb doesn't need to be
justified as a stress scenario), **native embb traffic (4000 Kbps) was
chosen as the most realistic possible target for the cold-start sweep**
-- the strongest possible realism argument available for any slice
tested in this project.

## 2. Phase 2: cold-start fixed-ceiling sweep at native load (4000 Kbps)

Same cold-start discipline as D/E1/E1b: gate on a throwaway stack, full
fresh restart, ceiling fixed before any traffic, buffer confirmed
drained (0.0%) before traffic at all 6 runs, >=120s hold (8 samples),
randomized order (seed 44007) = 5, 9, 17, 13, 25, 21. Ceilings extended
above the milestone's suggested {5,7,9,11,13,15} to {5,9,13,17,21,25},
since native demand (mean=17.27, max=23) already exceeded the
suggested range's upper end. `--out-dir` used throughout (the near-miss
found in E1b), so no file conflation risk. Zero `new_max_retx_events`
across all 48 samples, all 6 ceilings.

Steady-state (mean +/- population stdev, last 4 of 8 samples):

| ceiling (raw PRB) | served_kbps | loss_pct | rlc_rejected_pct |
|---|---|---|---|
| 5 (the floor) | 3857.8 +/- 44.3 | 0.00 +/- 0.00 | 0.00 +/- 0.00 |
| 9  | 3997.5 +/- 0.8 | 0.00 +/- 0.00 | 0.00 +/- 0.00 |
| 13 | 3997.2 +/- 0.7 | 0.00 +/- 0.00 | 0.00 +/- 0.00 |
| 17 | 3997.8 +/- 0.3 | 0.00 +/- 0.00 | 0.00 +/- 0.00 |
| 21 | 3996.6 +/- 0.3 | 0.00 +/- 0.00 | 0.00 +/- 0.00 |
| 25 | 3997.3 +/- 0.7 | 0.00 +/- 0.00 | 0.00 +/- 0.00 |

Offered load was a constant 4000 Kbps throughout. Every single ceiling
-- including 5, the absolute scheduler floor -- shows essentially full
health: zero loss, zero RLC rejection, zero max-RETX events, at every
sample from t=15s through the end of every 120s+ hold (no delayed onset
of the kind seen in urllc's and mmtc's degraded ceilings). The floor
itself shows only a small, clean, ~3.6% shortfall (3857.8 vs 4000
Kbps) with no loss or rejection signal at all -- a materially milder
effect than either urllc's or mmtc's floor behavior under their own
realistic loads.

## 3. Answering GATE E2's three questions

**(1) embb's band -- graded region y/n, how many points, raw-PRB
range?** No graded region was found in the tested range. All six
ceilings from 5 (the absolute floor) through 25 raw PRB are
statistically indistinguishable full-health states, with the sole
exception of a small, clean, non-lossy ~3.6% throughput gap exactly at
the floor. This is not a "3-level band" the way urllc's is -- it is
uniform health across the whole tested range.

**(2) Does the band-producing load stay recognizably eMBB-like?**
Not applicable in the sense intended -- no band was produced at all.
But the load used (embb's own native rate, 4000 Kbps, 1x, zero
elevation) is by construction the single most realistic possible eMBB
load tested anywhere in this project; if a band exists for embb, it
was not found at this, the most defensible load.

**(3) Does embb hit its own AM-saturation cliff at high load, and
where?** Not observed anywhere in the tested range (5-25 raw PRB) at
native load. Whether one exists at a higher (but still recognizably
eMBB, per this milestone's own framing that sustained high-throughput
is eMBB's nature) offered load is genuinely unknown -- the demand ramp
in section 1 shows uncapped demand climbing well past 25 PRB at 3x-10x
native, so a cliff, if one exists, would need to be searched for at a
higher load and/or a higher ceiling range than tested here. **This is
not measured**, and is flagged as `TODO(MEASURE)`, exactly parallel to
how mmtc's E1 finding (no band at its own reference load) was resolved
by a follow-up at a higher load in E1b.

## 4. A finding that revises this milestone's own working assumption

The milestone's framing (both in this message and in E3's own
still-pending synthesis instructions) treated "embb per E2" as if a
confirmed band was the expected outcome, parallel to urllc. The
measured result does not support that: **at its own most realistic
possible load, embb shows no shed band at all in the tested range,
including at the absolute scheduler floor.** This is reported plainly
rather than smoothed over -- embb's realistic-load controllability is
an open question, not a confirmed second data point alongside urllc.

## 5. What has NOT been done yet
- No higher-load re-sweep for embb (the natural analogue of E1b) has
  been run -- whether embb has a realistic-load band at some multiplier
  above native remains `TODO(MEASURE)`.
- The E3 common-regime/controllability synthesis (which this same
  milestone message also specified, as analysis-only, no new live
  testing) is addressed separately below, using embb's actual measured
  result (no band at native) rather than the anticipated one.
