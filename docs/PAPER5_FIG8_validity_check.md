# Fig. 8 live-anchor data validity check (2026-09-06)

## Why this check happened

M41's investigation (`docs/PAPER5_M41_envelope_sweep.md`) found and fixed
a real bug: `saclb_live.yaml`'s per-slice ceiling ratios (urllc/embb/mmtc,
`nominal_ratio`/`min_ratio_floor`/`max_ratio_cap`) were all calibrated to
1-4% of this rig's ~106-PRB carrier -- 1-4 raw PRBs, always below
`pf_dl_slice()`'s hard `min_rbSize=5` scheduling guard
(`gNB_scheduler_dlsch.c:1061`). Any live E2 control write applying a
ratio from that range permanently stops new-transmission DL scheduling
for the affected slice, starving the DL-delivered STATUS/ACK traffic an
AM RLC sender depends on and exhausting its 32-retry budget within
seconds. This explained every RLC max-RETX failure across the M36-M41
history (empty envelope, universal ~10s onset regardless of cadence,
load, or magnitude) and was fixed by scaling the ratios so the floor
alone clears the hard minimum.

While scoping "what next" after M41, `docs/PAPER5_M37_M38_scoping.md`'s
own recommendation to reuse `m31_highconf`/`m34_realistic_retrain_check`'s
existing live-anchor data (the manuscript's published Fig. 8: original
checkpoint @ 3UE/6UE, recalibrated checkpoint @ 6UE) was checked against
this finding, since that data is real live data collected over the same
E2 control mechanism -- and the check surfaced a second, independent
instance of the identical bug class in a different config file.

## What was checked

`experiments/results/live/m31_highconf/3ue_20ep_omega_log.jsonl`
("Original, 3 UE" in the manuscript's Fig. 8) records real live ceiling
values, e.g. `"gnb-0:urllc": {"min_ratio": 1, "max_ratio": 3}` --
confirming this run went through the real E2 control loop (not an
offline simulator). `run_live_eval_arm.py`'s own docstring usage example
shows the config used for this evaluation family is
`experiments/configs/saclb_campaign.yaml`, not `saclb_live.yaml` --
a separate file, independently calibrated (per its own header comments,
against this campaign's real measured traffic), but with the identical
structural flaw:

| Slice | nominal | floor | cap | -> raw PRBs (of ~106) |
|---|---|---|---|---|
| urllc | 2% | 1% | 4% | 2 / 1 / **4** |
| embb | 3% | 1% | 12% | 3 / 1 / **12** |
| mmtc | 2% | 1% | 3% | 2 / 1 / **3** |

**urllc's and mmtc's entire configured range never clears the scheduler's
5-PRB floor, at any value, including the cap** -- unlike `saclb_live.yaml`
(where every slice's cap was also too low), only embb here has a cap
(12) that clears the floor; the other two are structurally incapable of
ever being scheduled for a new transmission once any control write
lands, regardless of which checkpoint or policy issues it. Confirmed by
direct calculation (`106*4//100 = 4`, `106*3//100 = 3`, both `< 5`) and
by git history (`saclb_campaign.yaml` predates the M41 fix and was never
touched by it -- it is a separate file).

## Live verification

Git dates confirm the historical data predates the M41 fix window
(`saclb_live.yaml`'s broken ratios: 2026-07-16 to 2026-09-05; the Fig. 8
data: Aug 25/27). Ran the actual **original checkpoint**
(`experiments/results/m8_live_anchor/offline_train/single_agent_dqn/seed900/train/dqn/offline_train/rep_0/checkpoint.pt`)
against the **real, unmodified** `saclb_campaign.yaml` at native
(1x, "3UE"-equivalent) load through `m41_envelope_sweep.py`
(`--config`/`--checkpoint` overrides, no code changes needed) for a
short 120s window.

**Result: failed at t=10.0s.** `urllc` hit 100% packet loss while
mmtc/embb stayed at 0% (so far -- the run stopped at first 100%-loss
reading, per the harness's standard monitor-loop behavior). Confirmed
via the UE-side console log: **19 `max RETX reached` events on ue3
(urllc)** -- the exact same signature M41's whole investigation is
about. This is fully consistent with the math above: urllc has zero
escape from the below-floor range (cap=4 is still <5), so it collapses
fastest and completely; mmtc is in the identical situation (cap=3) and
would be expected to collapse too, given enough time; embb starts
below-floor at reset (nominal=3) but has real headroom to escape toward
its cap=12 if the policy accepts enough requests to walk the ceiling up
-- consistent with why it stayed healthy for the 10s this test ran.

Not yet tested: whether raising `saclb_campaign.yaml`'s ratios (a
verification-only copy exists at
`experiments/configs/saclb_campaign_m41fix_test.yaml`, 6x-scaled
matching the `saclb_live.yaml` fix technique, NOT a re-measured
recalibration) prevents the collapse, and whether the "6UE" condition
(believed but not confirmed to be a 2x-load variant, based on
`m32_ood_check_original_ckpt.py`'s reference to a
`saclb_offline_live1gnb_2xload.yaml`-style config -- the exact mechanism
used for `m31_highconf`'s specific "6UE" condition was not traced with
full confidence) shows the same or a different pattern. Stopped here
rather than spend more live time, since the finding is already strong
enough to require a decision before proceeding either direction.

## What this means, and what it doesn't

**Confirmed, high confidence:** `saclb_campaign.yaml` -- the config
underlying the manuscript's live-anchor evaluations for M8/M31/M37/M38
-- has the same structural flaw M41 found and fixed elsewhere, and it
reproduces the exact RLC max-RETX collapse signature live, immediately,
using the real original checkpoint, at what should be the "3UE" healthy
condition.

**Not yet resolved:** why the manuscript's own published "Original, 3UE"
result reports healthy behavior (reward -7.091, zero collapsed
episodes, all 20 episodes) when this config's urllc slice appears
structurally unable to avoid collapse. Candidate explanations, none
confirmed:
- A methodological difference between this verification's traffic
  generation (`m41_envelope_sweep.py`'s iperf3-based profiles) and the
  original evaluation's (`traffic_profiles.yaml`-driven, referenced in
  `saclb_campaign.yaml`'s own header but not inspected in this check) --
  if the original urllc traffic pattern generates far less real backlog,
  the below-floor ceiling might not get exercised hard enough to matter
  within a 20-episode/~100-minute session, matching the established
  "insufficient real demand never triggers the failure" pattern from
  M41's own single-UE-native-load findings.
- A timeline mismatch: `saclb_campaign.yaml`'s own header notes urllc
  was "RESTORED" to the core at some point after being dropped for lacking
  a real MAC slice -- if `m31_highconf`'s specific run predates that
  restoration, its "3UE" condition might not have included a live urllc
  bearer at all despite the config listing it, meaning no real control
  write ever reached a live urllc slice to collapse.
- Something about this verification's own setup not matching the
  original evaluation harness (`run_live_eval_arm.py`/`saclb_xapp.py`)
  closely enough -- this check reused `m41_envelope_sweep.py`'s bring-up
  path, not the original scripts, and did not attempt to reproduce the
  exact historical invocation.

**Practical consequence:** the M37/M38 scoping doc's "current lean:
reuse the existing 3UE/6UE data" recommendation should not be treated as
settled until one of the above is resolved -- particularly for any cell
involving urllc's live ceiling control. This is a decision point for the
user, not something to resolve unilaterally: either trace the exact
discrepancy (would need the original traffic-profile/timeline details,
more live time), treat the existing Fig. 8 numbers as provisionally
suspect and re-collect fresh anchor data under a properly-scaled config
before proceeding with M37/M38, or some other resolution the user
prefers.
