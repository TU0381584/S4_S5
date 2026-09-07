# M44-E3 — GATE E3 report: realistic controllability verdict

## This is analysis only -- no new live testing was run. Synthesizes
## M44-D + M44-E1 + M44-E1b + M44-E2. Per this milestone's own
## instruction, no common-load multi-slice search was attempted (E1b
## already showed no realistic common regime is possible, since mmtc's
## band requires non-mMTC traffic).

## The synthesis table

| slice | realistic band exists? | load tested | offered vs. native | raw-PRB range | # stable distinguishable points |
|---|---|---|---|---|---|
| **urllc** | **YES** | 3600 Kbps | 12x native (300 Kbps) -- a defensible URLLC-under-load stress scenario | 6-8 raw PRB (8+ full health) | 3: full health (8+), near-full/small-shortfall (7), substantially degraded but bounded (6) |
| **mmtc** | **NO**, under realistic mMTC traffic | 2500 Kbps (E1) | 50x native's own floor-clearing reference -- itself the load M44-A used to define "clears the floor," already the most defensible mmtc load available | 5-9 raw PRB | 0 -- uniformly healthy; only a small, clean, non-lossy ~11% gap at the floor |
| mmtc (for context only, NOT realistic) | YES, but only here | 4000 Kbps (E1b) | 80x native peak / ~320x true average (native is bursty 2s-on/6s-off, 12.5 Kbps true average) -- explicitly non-mMTC-like, sustained continuous traffic | 5-7 raw PRB | 3: full health (8+), moderate bounded degradation (6-7, indistinguishable from each other), severe bounded degradation (5, the floor) |
| **embb** | **UNRESOLVED** | 4000 Kbps (E2) | 1x native, zero elevation -- the single most realistic load tested for any slice in this project | 5-25 raw PRB | 0 in the tested range -- uniformly healthy even at the absolute 5-PRB floor (~96% served, zero loss/rejection); whether a band exists at a higher, still-eMBB-like load (demand climbs well past 25 PRB by 3-10x native, per E2's own ramp) is `TODO(MEASURE)`, not tested |

## The controllability verdict

**Only urllc has a confirmed, realistic, graded shed band on this
ratio-ceiling surface.** It is the sole slice for which this project has
directly measured a real, bounded, multi-point degradation region,
reachable at a traffic load that is itself a defensible representation
of that slice's own nature under load (a URLLC application legitimately
can face periods of elevated demand; 12x native is a stress scenario,
not a category change).

**mmtc cannot be admission-controlled on this surface under realistic
mMTC traffic.** Its own floor-clearing reference load (2500 Kbps, the
load M44-A itself established as representative) shows no shed band at
all -- not even at the scheduler floor. A band does exist, but only
once mmtc's traffic is driven at ~320x its true average native rate as
a sustained continuous stream, which is not mMTC traffic in any
meaningful sense; a graded admission decision exercised in that regime
would be controlling a slice mislabeled "mmtc" that is actually behaving
like a moderate continuous flow, not the real application class the
slice is meant to represent.

**embb's controllability is genuinely unresolved, not confirmed.** This
is the one place where this synthesis cannot give the answer the
milestone's own framing anticipated. At the single most realistic load
available (embb's own unmodified native traffic), the entire tested
range from the absolute scheduler floor up to 25 raw PRB is uniformly
healthy -- there is no evidence of ANY shed band, degraded region, or
AM-saturation cliff at native load. This could mean either (a) embb
genuinely has no realistic-load shed band on this surface at all
(its large, efficient 1200-byte packets may simply not stress the RLC
AM buffer the way urllc's small packets do, regardless of PRB
constraint), or (b) a band exists but only surfaces at a higher offered
load than native -- and per E2's own demand ramp, embb's uncapped
demand keeps climbing well past 25 PRB from 3x-10x native, so if a band
exists it is likely to require testing well above where this pass
stopped. Neither possibility has been distinguished by measurement.
**This synthesis does not invent an answer here** -- it reports the
open question as open.

## What this means for scoping the head-to-head (not started here)

Per this milestone's own explicit instruction, any DQN-QoE-vs-baseline
admission-control comparison should be **per-slice, in each slice's own
realistic regime, not a common-load joint campaign** -- E1b already
closed the door on a shared multi-slice regime, since mmtc's only band
requires abandoning realistic mMTC traffic entirely. Concretely, as of
this report:
- A urllc-only campaign at ~3600 Kbps / 6-8 raw PRB is fully scoped and
  ready to design, using M44-D's own measured band.
- An mmtc-only campaign under realistic traffic is not possible on this
  surface -- there is nothing to admission-control (E1's own finding).
  A campaign at mmtc's unrealistic E1b load could be built, but would not
  be evaluating mMTC admission control in any meaningful sense, and
  should not be presented as such without that caveat carried forward
  explicitly.
- An embb campaign cannot yet be scoped -- whether embb has a realistic
  shed band at all is still open, and scoping a campaign before knowing
  where (or whether) one exists would risk repeating GATE C's own
  original mistake (building on an unverified premise).

## STOP

This closes control-surface characterization (D, E1, E1b, E2, E3).
Awaiting go before scoping the head-to-head, per this milestone's own
explicit final instruction. If further embb load-elevation testing
(the natural analogue of E1b) is wanted before scoping, that is a
separate, not-yet-authorized next step, not assumed here.
