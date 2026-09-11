# M46-MR3b — locating the origin of MR3's uncapped-ceiling excursions

## CORRECTION (2026-09-11, from M46-MR3c): the "residual recurring pattern" below is retracted

The "smaller, still-open residual finding" section below (and the
corrected-but-still-partial state-responsiveness figures computed
alongside it) used a fixed `t>=30s` steady-state cutoff to exclude the
startup gap. M46-MR3c checked this properly, using each slice's own
TRUE first-`e2_apply`-write timestamp (already logged, just not used
this way yet) instead of a fixed cutoff: **that timestamp is ~93-103s
for some slices/runs, well past the 30s cutoff used below** -- so what
looked like a "residual, post-settling recurrence" was still sitting
inside the same, single, already-explained startup gap, not a second
mechanism. Re-checked directly against both of this report's own
already-collected runs: restricting to samples after each slice's own
true first write, the uncapped rate is **exactly 0.00%**, both slices,
both runs, no exceptions. There is no second mechanism to isolate. The
state-responsiveness figures quoted below (urllc r=0.65-0.85, embb
r=0.51-0.73) are similarly retracted as still-partially-contaminated
by this same too-early cutoff -- MR3c measures these cleanly, with the
fix applied and no exclusion window needed at all, instead of
recovering them from the contaminated pre-fix run. See
`docs/PAPER5_M46_MR3c_clean_revalidation.md` for the clean numbers.

Diagnostic-only, no retraining, no Path A decision (per this milestone's
own explicit gating). MR3 found the live-commanded ceiling (`M41DBG`
`max_prbs`) reading ~106 (the cell's full `n_rb_sched_init`) a large
fraction of samples in every run, with real backlog pending. MR1's
action space is confined to raw-PRB values `{6,7,8}`/`{5,...,10}` --
the policy cannot itself decode to 106 -- so the milestone's own framing
was correct that this is a control-path question, not evidence the
policy chose that action. This report locates exactly where the 106
comes from, and in the process finds and corrects a real error in
MR3's own severity characterization (see "Correction to MR3" below --
read that section regardless of which classification branch matters
to you).

## Method

Two phases, per this milestone's own instruction to minimize live time
before it's earned: (1) re-examine data MR3 already collected, using
instrumentation ALREADY present in the gNB binary that MR3's own
analysis never looked at; (2) add new instrumentation only for the
question phase 1 couldn't answer, then confirm live.

### Phase 1 -- free, from MR3's own already-collected logs

MR3's gNB logs already contain an `M41DBG e2_write` line, printed
inside `apply_slicing_ctrl()` (`e2_message_handlers.c`) at the exact
moment an E2 control message is received and parsed -- this is layer
(ii), the value actually written, independent of anything the
scheduler later does with it. Re-parsed all 4 of MR3's gNB logs for
this line: **every single E2 write in every run is a clean, in-band
ratio (e.g. `min_ratio=5 max_ratio=5`, `min_ratio=6 max_ratio=6`) --
never `(0,100)`.** Cross-referenced against `AdmissionGate.apply()`
(`framework/qoe_oran_framework/action_mapping.py`): `max_ratio` only
ever moves within `[min_ratio_floor, max_ratio_cap]` in steps of
`step_ratio`, and `min_ratio` is never touched by `apply()` at all
(only set once, to `spec.min_ratio_floor`, at `reset_ceilings()`) --
structurally incapable of producing `(0,100)`.

**This rules out the policy and the E2 write path (layers i and ii)
entirely, using zero new live time.** Whatever produces the uncapped
reading happens between `apply_slicing_ctrl()`'s write and the
scheduler's read.

### Phase 1 continued -- a wrong turn, corrected before it cost live time

Source-reading identified `SL_sched[i].max_prbs = n_rb_sched_init` as
the ceiling's un-clamped starting value (`gNB_scheduler_dlsch.c`),
computed inside what was first read as `pf_dl()`
(`gNB_scheduler_dlsch.c:1223`). Building `ninja nr-softmodem` to add
instrumentation there produced a real, checked warning: `'pf_dl'
defined but not used`. Grepped the entire `ORANSlice/` tree for any
call to `pf_dl(` -- none exists anywhere except its own definition.
**`pf_dl()` is dead code**, not what produces the `M41DBG
ceiling`/`postpf` lines MR3's (and this project's) existing parsers
rely on. The live function is `dl_sched_unit()`
(`gNB_scheduler_dlsch.c:1464`, confirmed called from
`gNB_scheduler_dlsch.c:1675`), which independently contains the exact
same `max_prbs` computation and `M41DBG` print. All instrumentation
below targets `dl_sched_unit()`, verified correct before any rebuild.
(A distinct earlier hypothesis -- that `slice_prb_estimate()`'s
per-slice `SL_sched[curSL].SL=SL; curSL++` population could leave
array slots uninitialized when a UE has zero buffered bytes -- was
also checked directly against the source and refuted: the assignment
happens unconditionally per slice, at the outer loop level, not gated
by the buffer check. Reported for completeness, not because it
matters going forward.)

### Phase 2 -- new instrumentation, live-confirmed

Two new log lines added (both temporary, tagged `M46DBG`, rate-limited
identically to the existing `M41DBG` lines to bound volume; full diff
at `docs/patches/m46_mr3b_control_path_instrumentation.patch`, since
`ORANSlice/` is gitignored per this project's standing convention):

1. `M46DBG e2_apply` in `apply_slicing_ctrl()` -- records the exact
   `NR_slice_info_t*`/`gNB_MAC_INST*` pointers the E2 write landed on,
   alongside the written ratio.
2. `M46DBG sched_read` in `dl_sched_unit()`, alongside the existing
   `M41DBG ceiling` print -- records the exact pointers the
   scheduler's READ resolved for the same NSSAI, alongside the ratio
   it read.

Rebuilt (`ninja nr-softmodem`, 6.4s incremental), ran 2 live seeds
(DQN-QoE, seeds 256/257 -- same checkpoints/config/E4 co-located
regime as MR3, `--out-dir experiments/results/m46_mr3b/` per this
milestone's own instruction, MR3's own already-committed results
untouched). Both runs: cold-start, contention gate PASS, `xapp
finished ok=True` (317.2s / 316.6s).

**Result: for every uncapped `sched_read` sample with a prior E2 write
for the same NSSAI, `sl_ptr` and `mac_ptr` are IDENTICAL to the
pointers recorded at that write.** This rules out classification 1's
"struct-instance mismatch" variant directly -- the scheduler is
reading the SAME memory `apply_slicing_ctrl()` writes into, not a
stale duplicate. The uncapped `(min_ratio=0, max_ratio=100)` is a
real, current value sitting in that exact struct at read time, not a
pointer-aliasing artifact.

## What actually explains it -- and a real correction to MR3

Cross-referencing `M46DBG e2_apply` timestamps against `M46DBG
sched_read`: in every one of the 6 runs now examined (MR3's original
4 plus this milestone's 2), **each NSSAI's very first E2 write of the
episode lands only once its first admission request is processed --
not at episode/reset time.** Traced this directly:
`RANEnv.reset()` (`framework/qoe_oran_framework/env.py:155-162`) calls
`self.gate.reset_ceilings()`, which only updates
`AdmissionGate`'s own in-memory Python dict to
`(min_ratio_floor, nominal_ratio)` -- **it never calls
`send_control()`.** The actual E2 write only happens inside
`env.step()`, and only for `(gnb_id, slice_id)` keys that had a
pending request that step. Until a slice's first request arrives, the
gNB's own `spolicy` for that NSSAI sits at whatever
`apply_slicing_ctrl()` last set it to -- which, at the start of a
fresh cold-start episode, is the gNB's own boot-time default from
`gnb_config.c` (`min_ratio=0, max_ratio=100`, applied before any E2
message has ever arrived this process's lifetime). This is confirmed,
not inferred: `dl_sched_unit()`'s `sched_read` events for urllc/embb
before their FIRST-ever `e2_apply` write are the entire population of
their earliest uncapped readings (12132/33248 = 36.5% of raw samples
in one MR3b run, for example) -- and once each slice's own first write
lands, its per-15s-window trajectory mean settles to a clean, stable
in-band value for the remainder of the episode (verified directly
against MR3's own already-committed per-window `trajectory` data, not
just MR3b's rerun -- see below).

**Correction to MR3's own report** (`docs/PAPER5_M46_MR3_live_trust_gate.md`):
that report characterized the uncapped ceiling as ~31-37% of the
episode based on raw M41DBG sample-frequency counts. Re-examining
MR3's own already-committed per-window `trajectory` data (which was
computed at the time but never looked at window-by-window before
writing that report) shows this was a real analysis error: **the
uncapped reading is concentrated almost entirely in window 0 (0-15s,
occasionally bleeding into window 1 for embb specifically, up to
~30s), then every window from there to the end of all 6 runs now
examined (urllc: all 6/6; embb: 6/6) is clean and stable** --

| run | urllc window0 mean | urllc window1+ | embb window0 mean | embb window1+ |
|---|---|---|---|---|
| MR3 qoe/256 | 96.2 | 6.0 (flat, w1-w20) | 92.3 | 5.3->5.0 (w1 elevated, w2+ flat) |
| MR3 qoe/257 | 105.5 | 6.0-6.4->6.0 (w1 elevated, w2+ flat) | 100.6 | 66.1->5.0 (w1 elevated, w2+ flat) |
| MR3 sla/256 | 97.1 | 7.6 (flat, w1-w20) | 92.2 | 32.0->9.6 (w1-w2 elevated, w3+ flat) |
| MR3 sla/257 | 97.3 | 6.4->7.6 (w1 elevated, w2+ flat) | 90.6 | 7.6->9.6 (w1-w3 elevated, w4+ flat) |
| MR3b qoe/256 | 96.1 | 5.75 (flat, w1-w20) | 87.2 | 5.0->4.7 (w1 elevated, w2+ flat) |
| MR3b qoe/257 | 96.0 | 6.0 (flat, w1-w20) | 98.8 | 59.3->5.0 (w1 elevated, w2+ flat) |

The raw-sample percentage MR3 reported is real (the numbers weren't
fabricated) but was **misleading as a measure of real-world impact**:
`M41DBG`/`M46DBG` logging is rate-limited to roughly 1-in-20 scheduler
calls, and the scheduler's own call rate is far from time-uniform --
disproportionately dense during the volatile first ~15-30s after
traffic launch (attach/RRC settling), which inflates that window's
share of the total LOGGED sample count well beyond its share of real
elapsed time. Weighted correctly by wall-clock time (the per-window
trajectory means, which MR3's own script already computed and wrote
to `results/m46_mr3/*/trajectory.jsonl`), the ceiling is uncapped for
roughly the first 15-30 seconds of a ~317-second episode (under 10%
of wall-clock time, not 31-37%), then correctly, stably in-band for
the remaining ~90%+.

**A smaller, still-open residual finding**: restricting to strictly
t>=30s (well past the settling window seen above) and looking at the
FULL distinct-value set (not window means, which wash out a small
number of samples), a lower-frequency (~15-19% of samples, i.e. still
inflated by uneven logging density, real wall-clock share almost
certainly much smaller) recurring return to the exact same
`(min_ratio=0, max_ratio=100)` signature persists in every run,
structured as either a few large multi-second bursts (MR3's qoe
arm, MR3b qoe/257) or many short (~7 logged samples, i.e. roughly
7x20=140 real scheduler calls) recurring blips at a fairly regular
~0.3-0.45s interval (MR3's sla arm, MR3b qoe/256). This shares the
exact same value signature and pointer identity as the startup gap,
so it is very likely the same underlying mechanism (something,
somewhere, causing the scheduler to observe this NSSAI's `spolicy`
before that cycle's write has landed) recurring at a much lower rate
after the episode is otherwise stable -- but this milestone did not
isolate its specific recurring trigger (unlike the startup gap, which
is fully explained above), and is reported honestly as open rather
than folded into the same explanation without direct evidence.

**Corrected state-responsiveness** (Pearson r, commanded ceiling vs
live backlog, recomputed on t>=30s samples only -- i.e. excluding the
startup-gap-dominated period MR3's original correlation was computed
over): urllc r=0.65-0.85 (was reported as 0.18-0.44), embb
r=0.51-0.73 (was reported as -0.05 to +0.19, "near-null"). The startup
gap's large, uniform block of `(uncapped-ceiling, small-remainUEs)`
points was diluting what is actually a substantially stronger
live-backlog-tracking relationship than MR3 reported for both slices,
not just urllc.

## GATE MR3b classification

**Classification 1 -- COMMAND-APPLICATION BREAK**, precisely located:
`RANEnv.reset()` (via `AdmissionGate.reset_ceilings()`) sets the
intended starting ceiling in Python only, and never pushes it to the
gNB via `send_control()`; the real applied ceiling for each NSSAI
stays at the gNB's own boot default until that slice's first
admission request is processed. This is upstream of, and unrelated
to, PF2-0's coupling confound -- it would reproduce identically in
ANY environment (coupled or independent), live or not, because it is
a Python-environment initialization gap, not a live-dynamics effect.
**Not** classification 2 (state-construction fallback -- the state
Python constructs was never shown to be malformed; this is about
what Python fails to SEND, not what it received) and **not**
classification 3 (genuine policy -- the policy's own decoded actions
are provably incapable of producing this value, confirmed both by
`action_mapping.py`'s range clamp and by the E2-write log showing
every actual write is clean).

The smaller residual recurring pattern (still ~15-19% of logged
samples post-settling, real-time share not yet isolated) carries the
identical signature and most plausibly belongs to the same
classification, but its specific trigger was not directly confirmed
this milestone and is flagged as open rather than asserted.

## What this does NOT establish

Does not fix anything -- per this milestone's own gating, no source
fix was applied (only diagnostic `M46DBG` logging, listed in the
attached patch). Does not, on its own, resolve GATE MR3's broader
verdict (PWC/shed classification, the qoe-vs-sla behavioral split) --
those findings did not depend on the mischaracterized severity
corrected here and are not reopened by this report. Does narrow what
"fix" means considerably: this reads as a straightforward environment-
initialization gap (push each slice's post-`reset_ceilings()` starting
ceiling via `send_control()` before the first step, closing the window
before any request has arrived), not evidence that a coupled-training-
environment retrain (Path A) is needed -- Path A was scoped specifically
to address PF2-0's cross-slice coupling confound, and this finding
does not implicate that confound at all.

## STOP

GATE MR3b classification: command-application break (1), root cause
identified in `RANEnv.reset()`/`AdmissionGate.reset_ceilings()`'s
missing initial `send_control()` push, confirmed via live pointer-
identity instrumentation plus a corrected, wall-clock-weighted re-
reading of MR3's own trajectory data (which also corrects that
report's state-responsiveness figures upward for both slices). A
smaller residual recurring instance of the same signature remains
open, not yet isolated to a specific trigger. Per this milestone's own
gating: awaiting go on whether to (a) apply the straightforward
initialization fix (push ceilings at reset) and re-run MR3, (b)
first isolate the residual recurring pattern before fixing anything,
or (c) something else -- not decided unilaterally here. Path A
(coupled retrain) is not indicated by this finding.
