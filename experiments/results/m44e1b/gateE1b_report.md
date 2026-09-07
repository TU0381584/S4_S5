# M44-E1b — GATE E1b report: mmtc's graded band at a higher, demand-matched load

## Verdict: YES, a real three-level graded band exists for mmtc once the
## offered load is raised to where uncapped demand reaches ~9-10 raw PRB
## (matching urllc's own band-producing regime) -- but reaching it required
## pushing mmtc's traffic profile well outside anything recognizably
## mMTC-like. STOPPING per this milestone's own "await go before E2"
## instruction.

## 1. Phase 1: finding the ~9-PRB load (wide-open ceiling ramp)

E1 found mmtc clears its own 50x/2500Kbps floor-clearing load with no
band at all. Interpolating M44-A's own committed mmtc demand curve
(50x->7.07 PRB mean, 100x->18.53 PRB mean, log-log fit) put the ~9 PRB
crossing near ~59x -- a fine ramp (52,55,58,60,62,65,70,75,80x) at a
wide-open ceiling, on a fresh stack past gate, measured it directly
instead of trusting the interpolation:

| mult | offered | target rnti mean PRB | max PRB |
|---|---|---|---|
| 52x | 2600 Kbps | 6.73 | 8.0 |
| 55x | 2750 Kbps | 6.93 | 8.0 |
| 58x | 2900 Kbps | 7.33 | 9.0 |
| 60x | 3000 Kbps | 7.40 | 8.0 |
| 62x | 3100 Kbps | 7.53 | 8.0 |
| 65x | 3250 Kbps | 9.87 | 38.0 (noisy outlier -- high max/mean ratio, not used) |
| 70x | 3500 Kbps | 8.60 | 10.0 |
| 75x | 3750 Kbps | 8.80 | 10.0 |
| 80x | 4000 Kbps | 9.87 | 12.0 |

Chose **80x / 4000 Kbps** for phase 2: closest mean (9.87) to urllc's own
M44-D reference demand (mean=10.20, max=13.00) with a comparable,
well-behaved max/mean ratio (12/9.87=1.22 vs urllc's 13/10.20=1.27),
avoiding 65x's noisy 38.0 max outlier. The other two slices' rntis
stayed flat at 5.00 PRB (floor artifact) throughout, confirming the
elevated rnti was genuinely mmtc's own.

## 2. Phase 2: cold-start fixed-ceiling sweep at 4000 Kbps

Same cold-start discipline as M44-D/E1: gate on a throwaway stack, full
fresh restart, ceiling fixed before any traffic, buffer confirmed
drained (0.0%) before traffic at all 6 runs, >=120s hold (8 samples),
randomized order (seed 44006) = 5, 7, 10, 9, 6, 8. Wrote to a separate
`experiments/results/m44e1b/` directory (a bug caught before any data
was written: the script's default output dir is shared across all runs
for a slice, so a first attempt at this higher load would have appended
into the SAME `trajectory_mmtc_ceil{N}.jsonl` files as E1's 2500Kbps
data for ceilings 5-9, conflating two different offered-load datasets in
one file -- caught and killed within seconds of noticing, before any
data was written; fixed by adding a `--out-dir` override to
`m44e_coldstart.py` and re-running clean). Zero `new_max_retx_events`
across all 48 samples, all 6 ceilings.

Steady-state (mean +/- population stdev, last 4 of 8 samples):

| ceiling (raw PRB) | served_kbps | loss_pct | rlc_rejected_pct |
|---|---|---|---|
| 5 | 2129.8 +/- 20.4 | 47.28 +/- 0.57 | 46.74 +/- 0.67 |
| 6 | 2921.7 +/- 9.9  | 27.02 +/- 0.84 | 24.85 +/- 0.53 |
| 7 | 2904.8 +/- 80.8 | 27.02 +/- 0.71 | 25.81 +/- 2.31 |
| 8 | 4025.0 +/- 20.0 | 0.00 +/- 0.00  | 0.00 +/- 0.00  |
| 9 | 3999.8 +/- 0.3  | 0.00 +/- 0.00  | 0.00 +/- 0.00  |
| 10 | 3999.8 +/- 0.5 | 0.00 +/- 0.00  | 0.00 +/- 0.00  |

Offered load was a constant 4000 Kbps throughout. Every degraded ceiling
(5, 6, 7) showed the same onset shape as urllc's own 6-PRB M44-D
trajectory: clean for the first ~55-75s, then real loss/rejection
appearing and settling into a bounded (not worsening, not collapsing)
steady state by ~100s -- confirming again that a hold shorter than
~120s would have missed the true steady state.

## 3. Answering GATE E1b's three questions

**(1) mmtc's band at this higher load -- graded region y/n, how many
points, at what PRB range and load?**

Yes. Three distinguishable, stable levels at 4000 Kbps offered:
- **8-10 raw PRB**: full health, statistically indistinguishable from each other.
- **6-7 raw PRB**: a real, bounded, moderate-degradation plateau -- 6 and 7 PRB are themselves statistically indistinguishable from each other (~2905-2922 Kbps served, ~27% loss, ~25% rejection), i.e. widening the ceiling from 6 to 7 PRB does not measurably help at this load.
- **5 raw PRB** (the floor): a real, bounded, substantially more severe degradation (~2130 Kbps served, ~47% loss, ~47% rejection) -- clearly distinct from the 6-7 PRB plateau.

So: a graded (non-binary) band exists, but its internal structure is two
plateaus (moderate at 6-7, severe at 5) rather than three fully
separated points the way urllc's band had one point per raw-PRB step.

**(2) Does this load keep mmtc recognizably mMTC-like, or was an
atypical profile required?**

Atypical -- and by a wide margin. mmtc's native profile
(`traffic_profiles.yaml`) is bursty: 50 Kbps for a 2s window, then 6s
idle (25% duty cycle), 80-byte packets -- a true average throughput of
only 12.5 Kbps. The 4000 Kbps load used here is **sustained and
continuous** (no on/off cycling, matching this whole project's
established methodology for demand-ramp and cold-start probing), and is
**80x mmtc's own peak burst rate** and **~320x its true average native
rate**. Packet size (80B) stayed native, but the traffic's temporal
character (continuous vs. bursty) and absolute sustained rate are both
far outside anything a real mMTC application would plausibly generate.
This is flagged here explicitly, not glossed over: any DQN-QoE-vs-
baseline campaign that exercises mmtc's graded band at this load is
implicitly testing "a slice labeled mmtc carrying an embb-scale
sustained flow," not a realistic mMTC traffic pattern.

**(3) How does mmtc's band load compare to urllc's ~3600Kbps/~9-PRB
regime -- same load or different?**

Different, in two senses. In absolute Kbps the two loads are close
(4000 vs 3600, ~11% apart) and both were chosen by the same method
(closest match to a ~9-10 PRB uncapped mean demand). But relative to
each slice's own native characteristic rate, the two loads are worlds
apart: urllc's 3600 Kbps is 12x its native 300 Kbps sustained rate --
a large but not inherently absurd stress multiplier for a real-time
low-latency application under load. mmtc's 4000 Kbps is 80x its native
*peak* rate and ~320x its true average rate -- a categorically larger
departure from the slice's own defining traffic character. Getting
mmtc into the same absolute PRB-demand regime as urllc required a
proportionally far more extreme push away from "what mmtc actually is."
This asymmetry is directly relevant to E3's common-regime question and
is handed off as-is, not resolved here.

## 4. What has NOT been done yet
- embb (E2) has not been started.
- The common-regime search (E3) has not been started -- and per (2)/(3)
  above, it inherits an open question about whether exercising mmtc's
  band at all is representative of anything mMTC-like, which E3 (or a
  decision above it) will need to account for rather than this report
  resolving on its own.
