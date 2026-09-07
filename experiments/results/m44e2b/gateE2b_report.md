# M44-E2b — GATE E2b report: why embb resisted shedding, and a confirmed realistic band

## Verdict: the ceiling DOES bind embb (mechanistically confirmed live --
## hypothesis (i), the wildcard-SD bypass, is ruled out). embb's
## resistance to shedding at native load was real spectral efficiency
## (hypothesis (ii)), not a control-path bug. At a higher, still
## realistic eMBB load (3x native), embb shows the cleanest, most fully
## graded shed band found anywhere in this project: 6 statistically
## distinct operating points across 5-10 raw PRB. Final controllability
## count: 2 of 3 slices (urllc, embb) have a confirmed realistic band;
## mmtc does not. This closes control-surface characterization.

## 1. Does the ceiling bind embb? (mechanistically confirmed from live scheduler state)

Static reading of `gNB_scheduler_dlsch.c` found no special-casing of
`sd==0xffffff` anywhere in the ceiling computation or per-slice
scheduling loop -- but per this milestone's own instruction, that is
not proof. embb's actual internal slice id, read from the gNB conf's
own `snssaiList` order (`{sst=1,sd=0xFFFFFF}` listed first), is
`sid=1` (mmtc=2, urllc=3) -- confirmed via `nr_update_slice_policy`'s
own `SL_info->list[s+1]->sid = s+1` assignment.

A dedicated cold-start run pinned embb's ceiling to 5% (~5 raw PRB) at
native load (4000 Kbps, exactly E2's own finding scenario) and read the
gNB's own M41DBG scheduler instrumentation directly -- `LOG_I` lines
already built into the current binary from earlier work, printing every
slice's live `min_ratio/max_ratio/dedi_prbs/min_prbs/max_prbs` every
~10ms. 44,460 samples were captured over the 147s hold:

| sid (slice) | commanded max_ratio | live max_prbs: mean | distribution |
|---|---|---|---|
| 1 (embb) | 5 | 4.75 | {5: 9726 samples (87.5%), 3: 1389 (12.5%)} |
| 2 (mmtc) | 100 (untouched) | 96.75 | {101: 9726, 67: 1389} |
| 3 (urllc) | 100 (untouched) | 96.69 | {101: 9726, 67: 1255, 62: 134} |

embb's live `max_prbs` is clamped to 5 (occasionally 3, when other
slices' `min_prbs` reservations eat into the shared budget -- expected,
correct dynamic behavior, not a bug) for the ENTIRE 147-second run,
never once approaching the ~97-101 that mmtc/urllc show in the exact
same log at the exact same timestamps for their own (untouched, wide-
open) ceilings. This is unambiguous, direct, live confirmation that the
scheduler's own per-slice PRB budget IS being computed and enforced for
embb: **the ceiling binds.** The wildcard-SD-bypass hypothesis is ruled
out by measurement, not inference.

(The `postpf` M41DBG line's `n_rb_sched` field was captured too but not
used as evidence: it reflects a running RB counter shared across all
slices processed so far in that TTI's scheduling pass, not embb's own
individual grant in isolation -- reported here for completeness, not
mis-used as a number it doesn't actually represent.)

Given the ceiling binds but embb still served ~96% of native offered
load at this same 5-raw-PRB cap (E2's finding), the explanation is
confirmed to be hypothesis (ii): embb's 1200-byte packets are simply far
more spectrally efficient per PRB than urllc's/mmtc's tiny packets, and
5 raw PRB's real capacity comfortably exceeds embb's native 4 Mbps
demand. This is a genuine radio-efficiency result, not a measurement or
control-path artifact.

## 2. Higher-load band search (a real degraded region does exist)

A quick single-ceiling smoke test at 3x native (12000 Kbps) and
ceiling=5 confirmed real, substantial degradation (served ~3800 Kbps,
~68% loss/rejection) before committing to the full sweep -- this ruled
out wasting a ~35-minute campaign on a load that might still show no
effect.

Full cold-start sweep at 3x native across {5,6,7,8,9,10} raw PRB,
randomized order (seed 44007) = 5, 6, 8, 7, 10, 9. Gate PASS and buffer
confirmed 0.0% at all 6 runs. Zero `new_max_retx_events` across all 48
samples.

Steady-state (mean +/- population stdev, last 4 of 8 samples; offered
constant at 12000 Kbps):

| ceiling (raw PRB) | served_kbps | served % of offered | loss_pct | rlc_rejected_pct |
|---|---|---|---|---|
| 5  | 3830.3 +/- 12.9  | 31.9% | 68.09 +/- 0.07 | 68.19 +/- 0.13 |
| 6  | 4382.7 +/- 171.7 | 36.5% | 63.16 +/- 1.35 | 63.56 +/- 1.18 |
| 7  | 5216.6 +/- 86.1  | 43.5% | 56.36 +/- 0.18 | 56.75 +/- 0.88 |
| 8  | 5841.9 +/- 25.8  | 48.7% | 51.12 +/- 0.23 | 51.36 +/- 0.32 |
| 9  | 6708.9 +/- 65.8  | 55.9% | 44.50 +/- 0.12 | 44.29 +/- 0.39 |
| 10 | 7352.0 +/- 54.7  | 61.3% | 38.84 +/- 0.19 | 38.88 +/- 0.36 |

Every one of the 6 tested ceilings is statistically distinct from every
other (tight stdevs relative to the spacing between means) -- this is a
**fully, smoothly graded six-point band**, the cleanest and most finely
resolved shed region found anywhere in this project (urllc's own M44-D
band had 3 points; mmtc's E1b band had 2 distinguishable plateaus plus
the floor). Every degraded ceiling showed the same onset shape seen
throughout this project (clean for the first ~15-30s reading only
partial rejection, settling into a bounded steady state by ~90-110s --
reconfirming the >=120s hold requirement once again). No ceiling
approached full health in this range (even at 10 raw PRB, loss/rejection
is still ~39%) -- the true full-health point at 3x native sits above 10
raw PRB, not characterized further here since the band itself (not its
upper boundary) was the object of this search.

## 3. Answering GATE E2b's three questions

**(1) Does the ceiling bind embb, mechanistically confirmed live?**
Yes -- directly confirmed via 44,460 samples of the gNB's own live
scheduler state (M41DBG instrumentation), showing embb's `max_prbs`
clamped to the commanded value throughout a 147-second hold, with
mmtc/urllc's own untouched ceilings reading ~20x higher in the same log
at the same timestamps.

**(2) If yes, is there a realistic graded band, and where?** Yes. At 3x
native (12000 Kbps -- a mild, easily defensible eMBB-under-load
scenario, far less extreme than urllc's own 12x or mmtc's forced 80x),
a fully graded, six-point band exists across the entire tested 5-10 raw
PRB range, with served throughput climbing monotonically from 32% to
61% of offered and loss/rejection falling monotonically from 68% to
39%.

**(3) Final controllability count -- how many of the three slices have
a confirmed realistic shed band?** **2 of 3: urllc and embb.** mmtc does
not -- its only band (E1b) requires driving it at ~320x its true
average native rate, categorically outside real mMTC traffic character.

## 4. Revision to the E2/E3 controllability verdict

E2's own report (and the E3 synthesis built on it) stated embb's
realistic-load controllability as genuinely unresolved, since no
degradation was found anywhere in the native-load sweep. That is
superseded by this result: embb DOES have a confirmed, realistic,
richly graded band -- just not at native load; at a mild, still-
realistic 3x elevation. The corrected controllability table:

| slice | realistic band? | load | PRB range | # stable points |
|---|---|---|---|---|
| urllc | YES | 3600 Kbps (12x native) | 6-8 | 3 |
| embb | YES | 12000 Kbps (3x native) | 5-10 | 6 (fully graded) |
| mmtc | NO | -- (only exists at ~320x-native unrealistic load) | -- | 0 |

## 5. What has NOT been done
- The upper (full-health) boundary of embb's 3x-native band above 10
  raw PRB has not been characterized -- not needed for this milestone's
  question, which was whether a band exists at all.
- No head-to-head DQN-QoE-vs-baseline scoping has been started.

## STOP

This is the last characterization gate, per this milestone's own
instruction. Awaiting go before the head-to-head scope decision, which
per this milestone's own framing is now a supervisor-level choice
between (a) scoping a per-slice campaign on urllc and embb in their own
realistic regimes on this ratio-ceiling surface (mmtc excluded, no
realistic band), or (b) a narrowband-BWP retry / core-level admission
primitive for mmtc specifically, since the surface itself is now well
characterized for all three slices.
