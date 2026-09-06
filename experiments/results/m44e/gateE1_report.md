# M44-E1 — GATE E1 report: mmtc cold-start graded-band characterization

## Verdict: NO graded shed band found in the tested range (5-9 raw PRB) at
## this offered load. mmtc is essentially uniformly healthy across the
## entire floor-to-well-above-demand range, with only a marginal, clean
## (zero-loss, zero-rejection) ~11% admission gap right at the 5-PRB
## floor itself. This is a genuinely different signature from urllc's
## M44-D finding, not a bug. STOPPING per GATE E1's own "await go"
## instruction -- E2 (embb) not started.

## 1. Protocol run

Same cold-start discipline as M44-D: contention gate on a throwaway
stack, full fresh docker+gNB+UE restart, ceiling fixed to the target
value BEFORE any mmtc traffic existed, `dl_mac_buffer_occupation`
confirmed 0.0% before traffic at every one of the 5 runs, then a
constant 2500 Kbps offered load (50x native, per this milestone's own
instruction and M44-A's calibration: real uncapped demand at this load
is ~7.07 raw PRB, mean, per M44-A's `demand_curve_mmtc.jsonl`), held for
>=120s (8 samples every ~15-22s) per ceiling. Ceilings {5,6,7,8,9} raw
PRB, randomized order (seed 44006) = 7, 9, 5, 6, 8. Zero
`new_max_retx_events` across all 40 samples, all 5 ceilings.

One bug from M44-D (stdbuf block-buffering) was already fixed upstream
in `m44c_shed_sweep.py`'s shared `launch_reporting_traffic` before this
run; this milestone's own `launch_traffic()` (a slice-agnostic
duplicate, needed only because `m44a.SLICE_TRAFFIC` has no "embb" entry
for the later E2 run) carries the same `stdbuf -oL -eL` fix. No new bug
found this pass -- real data was present from the very first ~15s
sample at every ceiling, confirming the fix generalizes.

## 2. Steady-state summary (mean +/- population stdev, last 4 of 8 samples)

| ceiling (raw PRB) | served_kbps | loss_pct | rlc_rejected_pct | new_max_retx (whole run) |
|---|---|---|---|---|
| 5 | 2228.8 +/- 23.5 | 0.000 +/- 0.000 | 0.00 +/- 0.00 | 0 |
| 6 | 2510.2 +/- 10.2 | 0.000 +/- 0.000 | 0.00 +/- 0.00 | 0 |
| 7 | 2514.8 +/- 49.0 | 0.010 +/- 0.017 | 0.00 +/- 0.00 | 0 |
| 8 | 2500.3 +/- 0.3  | 0.000 +/- 0.000 | 0.00 +/- 0.00 | 0 |
| 9 | 2500.3 +/- 0.3  | 0.000 +/- 0.000 | 0.00 +/- 0.00 | 0 |

Offered load was a constant 2500 Kbps throughout.

Ceiling=5 (the scheduler floor itself) trajectory: opened at 2250 Kbps
(t=15s), drifted to a low of ~2182 Kbps (t=75s), then recovered and
settled at ~2190-2254 Kbps for the remainder of the 160s hold -- a
small, real, but bounded and *non-worsening* admission-limited gap
(~89% of offered), with exactly 0% loss and 0% RLC rejection at every
single sample, start to finish. Ceilings 6-9 all read essentially
identical to full health (served matching or slightly exceeding offered
within normal CBR-generator sampling noise, matching the same +/-1%
wobble seen at urllc's healthy points in GATE C/D).

## 3. Answering GATE E1's question

**Does a graded region exist above the floor? How many stable
distinguishable points, at what raw-PRB range and offered load?**

At 2500 Kbps offered (50x native): no. Across the entire tested range,
including right at the 5-PRB scheduler floor, mmtc never showed real
packet loss or RLC admission rejection. There is exactly one
distinguishable point -- ceiling=5, with a small, clean, ~11% throughput
shortfall against offered -- and it is not a "degraded" state in the
sense GATE C/D used for urllc (no loss, no rejection, not
progressively worsening over the full 160s hold). Ceilings 6 through 9
are statistically indistinguishable from each other and from full
health.

This contrasts with urllc's M44-D finding (a real three-point band: 8+
PRB healthy, 7 PRB near-full with a small shortfall, 6 PRB substantially
degraded with ~39% loss and ~37% RLC rejection) in a specific and
informative way: mmtc's smaller packets (80B vs urllc's 100B) and lower
absolute offered rate (2500 vs 3600 Kbps) apparently let the scheduler
serve nearly all of the offered load even at very few PRBs, without
building the kind of sustained RLC AM backlog that produced urllc's real
degradation. Whatever is limiting mmtc's throughput at the floor
(~11% short) is being absorbed cleanly -- consistent with an admission
timing/TBS-alignment effect rather than genuine buffer saturation.

## 4. What this does NOT establish

This is a negative/inconclusive result for the specific window tested,
not proof mmtc has no shed band anywhere. The milestone's own text
anticipated needing to "extend if the band sits elsewhere" -- the most
likely explanation is that 50x/2500 Kbps (chosen because it is mmtc's
own floor-clearing load per M44-A) simply does not create enough
scarcity pressure to reach mmtc's real transition; a materially higher
offered load (well above 5-9 PRB's serviceable capacity, analogous to
how urllc's 3600 Kbps was chosen because it sits close to its own
uncapped ~9-10 PRB demand) would be needed to find where mmtc's own
degradation region actually lives, if one exists in a usable band above
the floor at all.

**TODO(MEASURE):** the offered load at which mmtc produces a comparable
graded degradation to urllc's has not been measured. Not extended to a
higher-load re-sweep in this pass, since GATE E1 as specified asks to
report and await go before any further mmtc work, not to self-select a
new load and re-run.

## 5. What has NOT been done yet
- No re-sweep of mmtc at a higher offered load.
- embb (E2) has not been started.
- No common-regime analysis (E3) has been started.
