# M44-A: scarcity headroom at full 106-PRB carrier

Live. Standing constraints honored: `min_rbSize` never touched; no edits to
committed config/frozen source (target slice's ceiling forced wide open via
a direct `probe_e2_preconditions.py --send-control` write, an existing
unmodified tool, not a config change); contention gate run before every
measurement window; new logic only in `experiments/scripts/m44_scarcity_probe.py`
(new file).

## Method

For each target slice (urllc, then mmtc) separately: bring up the standard
3-UE stack, pass the contention gate, do a fresh post-gate restart (M41's
own established discipline), force the target slice's ceiling wide open
(`min=0,max=100`, direct E2 write, no policy running), then ramp that
slice's own offered bitrate through native, 2x, 5x, 10x, 20x, 50x, 100x
(mmtc also got 200x, given its much lower native rate). At each level,
settle 20s then poll real `avg_prbs_dl` for 15 samples via
`probe_e2_preconditions.py` (existing, unmodified). The other two slices
kept running their normal native traffic throughout (needed for the gate,
and to keep the carrier realistic rather than idle).

**A real bug was found and fixed mid-investigation, not a rig finding**:
the first urllc run's load levels beyond native (2x through 100x) all
silently hit the already-documented "server is busy running a test"
iperf3-target port-wedge bug — every ramped traffic client died on
connection, and the demand readings for those 6 levels were measuring
stale carryover from the native level, not real ramped traffic. Caught by
checking the traffic client's own log files (67-byte error files, not real
iperf3 output) after the run looked suspiciously flat. Fixed by recreating
the `iperf3-target` container between every load level (the established fix
elsewhere in this project, e.g. `run_stage15_n128_campaign.sh`'s own
`maybe_fix_iperf3()`) and added a hard check that the traffic client is
still alive before trusting a measurement. Re-ran urllc from scratch with
the fix; the results below are from the corrected runs.

**A real, previously-undocumented-in-this-form measurement artifact,
important for interpreting all of this data**: `avg_prbs_dl` reads exactly
`5.00` at every load level where the scheduler is granting anything at all
but demand hasn't yet forced a grant above the minimum. This is not
literally "demand equals 5 PRB" -- it is `min_rbSize=5` itself (the
scheduler's hard minimum grant size, confirmed and left untouched per M41)
setting a floor on the SMALLEST unit the scheduler can express, regardless
of how much smaller the real payload is. True underlying demand at these
low multipliers is very likely well below 5 PRB in raw terms; it reads as
a flat `5.00` because that is the finest granularity `avg_prbs_dl` can ever
show, not because 5 PRB is genuinely required. This matches config
comments already on record elsewhere in this project ("avg_prbs_dl flat at
the same 5.00 PRB idle floor... too coarse a signal at this traffic rate to
calibrate a cap from directly").

## Result: demand-vs-load curves

**urllc** (native 300 Kbps, target UE RNTI confirmed by tracking which of
the three attached UEs' `avg_prbs_dl` actually moved with the ramp):

| Load | Bitrate | avg_prbs_dl (mean/max) | RAM avail | RLC retx |
|---|---|---|---|---|
| 1x | 300K | 5.00 / 5.00 | 1121 MB | 0 |
| 2x | 600K | 5.00 / 5.00 | 1125 MB | 0 |
| 5x | 1500K | 5.00 / 5.00 | 1117 MB | 0 |
| **10x** | **3000K** | **7.00 / 7.00** | 1108 MB | 0 |
| 20x | 6000K | 19.27 / 29.00 | 1142 MB | 0 |
| 50x | 15000K | 100.20 / 106.00 | 1142 MB | 0 |
| 100x | 30000K | 85.07 / 106.00 | 1137 MB | 0 |

**mmtc** (native 50 Kbps):

| Load | Bitrate | avg_prbs_dl (mean/max) | RAM avail | RLC retx |
|---|---|---|---|---|
| 1x-20x | 50K-1000K | 5.00 / 5.00 (flat) | 1095-1118 MB | 0 |
| **50x** | **2500K** | **7.07 / 8.00** | 1146 MB | 0 |
| 100x | 5000K | 18.53 / 79.00 | 1170 MB | 0 |
| 200x | 10000K | 74.13 / 106.00 | 1219 MB | 0 |

**Real demand first clears the 5-PRB floor at 10x native for urllc (3 Mbps)
and 50x native for mmtc (2.5 Mbps)** — in absolute bitrate terms the two
slices' floor-clearing points are similar (~2.5-3 Mbps), which makes sense
given both carry small (80-100 byte) packets. Both slices then scale
cleanly upward with real headroom before approaching the 106-PRB carrier's
own ceiling (urllc saturates near 50x/15 Mbps; mmtc saturates near
200x/10 Mbps) — a wide window exists between "clears the floor" and
"saturates the carrier" for both slices. Zero RLC retransmission failures
and stable, non-degrading RAM at every level tested, for both slices —
no host-capacity wall was hit at any point in this probe.

## GATE A verdict

**Demand clears 5 PRB with real headroom to spare, for both urllc and
mmtc, at the full 106-PRB carrier.** Scarcity is reachable without
shrinking the carrier. Per the milestone's own gating: **proceed to M44-C,
skip M44-B** (the narrowband-BWP fallback is not needed).

Concretely, for the eventual M44-C ceiling-sweep test: a ceiling window
roughly in the 7-20 raw-PRB range (urllc ~12-19% ratio, mmtc ~7-19% ratio
on this ~106-PRB carrier) sits between "clears the scheduler floor" and
"the slice's own real demand at a reasonable stress multiplier (10-20x
native)" — this is the candidate operating range where a ceiling should be
able to bind against real demand without either falling below the floor
(M41's failure mode) or being so generous it never constrains anything
(the original problem this milestone exists to solve).
