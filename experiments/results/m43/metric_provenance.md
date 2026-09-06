# M43-P0: compliance-metric provenance + telemetry reconciliation

Read-only, no rig. No committed config/result/frozen source edited (frozen
files `kpm_adapter.py`/`reward.py`/`env.py` read only). All source lines
cited directly.

## 1. What "compliance" actually measures, traced end to end

**Frozen framework, `kpm_adapter.py:aggregate_slice_state()` (lines 42-90)**:
per slice, per gNB, per poll:
```
queue_raw = sum(u.dl_mac_buffer_occupation for u in ues)
if ues and queue_raw <= 0.0:
    queue_raw = sum(u.dl_errors + u.dl_bler for u in ues)   # fallback
    # flagged in `limitations`, not silent
queue_len_norm = min(2.0, max(0.0, queue_raw / Lmax))
loss_proxy = mean(u.dl_bler for u in ues)
```

**Frozen framework, `reward.py:check_violations()` (lines 69-90)**:
```
queue_violation = agg.queue_len_norm > 1.0
loss_violation  = agg.loss_proxy > spec.loss_budget_pct
violated        = queue_violation OR loss_violation
per_slice_compliant = NOT violated
margin = min(1.0, 1.0 - raw_queue_len_norm, 1.0 - loss_proxy/loss_budget_pct)
```

This is the exact formula behind every "compliant"/"violation" and every
`per_slice_sla_margin` value in every omega log, including the N128
campaign's headline compliance percentages.

**The decisive finding**: for a slice receiving **zero PRB grants** (M41/M42's
confirmed below-floor failure mode), no PDSCH transmission is ever attempted,
so:
- `dl_errors` (HARQ NACK-after-max-retransmission count) stays 0 — there is
  nothing to fail, because nothing was ever sent.
- `dl_bler` (block error rate) stays 0 — 0 errored blocks / 0 transmitted
  blocks is conventionally 0, not undefined-as-violation.
- Therefore `loss_proxy = 0`, and `loss_violation` is false regardless of
  `loss_budget_pct`.
- If `dl_mac_buffer_occupation` also reads 0 (see §2), the fallback
  (`dl_errors + dl_bler`) is *also* 0, so `queue_raw = 0`, `queue_len_norm = 0`,
  and `queue_violation` is false too.

**A fully-starved slice therefore satisfies BOTH compliance channels
simultaneously and reads back as `per_slice_compliant: true`,
`per_slice_sla_margin` ≈ 1.0 — the maximum possible score.** This is not a
bug in the fallback logic specifically; it follows directly from the
formula, independent of which of the two `queue_raw` sources is in effect.
**The metric is, by this construction, structurally insensitive to complete
DL scheduling starvation** — the one failure mode M41/M42 confirmed this
project's below-floor configs can produce.

## 2. Reconciling N128 (queue_raw≡0 throughout) vs M8 (100%/-10^6 magnitude)

Traced `dl_mac_buffer_occupation`'s gNB-side source
(`gNB_scheduler_dlsch.c:327-383`, `nr_store_dlsch_buffer()`, called
unconditionally every scheduling slot from `nr_fr1_dlsch_preprocessor()`
at line 1638 — **not** gated on whether that slice was actually granted any
PRBs this slot). It queries RLC's own `bytes_in_buffer` directly via
`mac_rlc_status_ind()` for every logical channel, every slot. In principle
this SHOULD reflect real, growing backlog for a starved slice with
continuously-arriving organic traffic, which is the opposite of what the
N128 logs show (a flat 0 for the entire campaign).

**Reconciliation, source-supported but not live-confirmed this pass
(flagged at the confidence level it deserves, not asserted as fact)**: PDCP
implements a standard 3GPP `discard_timer` mechanism
(`nr_pdcp_entity.c:613,661` — PDUs older than this timer are discarded, not
delivered). If a slice's DL bearer is granted zero PRBs for long enough,
arriving PDUs would be discarded at the PDCP layer once their timer expires,
**before ever being handed down into RLC's own queue** — meaning RLC's
`bytes_in_buffer` (the field `dl_mac_buffer_occupation` actually reports)
would show at most a small, timer-bounded transient, not unbounded growth,
and could plausibly read as 0 at the specific 5-second polling cadence this
campaign used. Under this hypothesis, the real consequence of starvation is
**silent upstream packet loss**, invisible to both of this framework's
chosen backlog proxies, not a queue that visibly grows.

This is a plausible, source-grounded mechanism, **not directly confirmed by
new live instrumentation in this P0 pass** (which would require tracing
PDCP-layer discard events specifically, live — out of scope for a no-rig
gate). Marked `TODO(MEASURE)` as the specific reconciliation mechanism;
what IS confirmed without qualification is §1's formula-level blindness,
which holds regardless of which specific reconciliation is correct.

M8's own methodology (a small number of long, continuous, undrained runs)
versus N128's (many short 2-episode batches, each preceded by
`drain_backlog.sh` resetting ceilings to `min=0,max=100` and waiting 20s to
verify drainage before starting) is a second plausible contributing factor —
M8 had far more continuous exposure time per unbroken run for any queueing
dynamics (real or discard-timer-mediated) to manifest differently than N128's
repeatedly-reset short batches. Also not independently confirmed; noted as a
second candidate contributor, not the sole explanation.

## 3. Could a correct, above-floor live re-run move this metric?

**Yes, in principle** — once a slice's ceiling clears the scheduler floor,
`nr_store_dlsch_buffer()`'s per-slot RLC query is a real signal, not a
placeholder; M8's own runs (same broken config, but different traffic
duration/pattern) demonstrably DID produce large non-zero readings from this
same code path. Nothing in the trace suggests `dl_mac_buffer_occupation` is
permanently non-functional on this rig — only that it is specifically blind
to the zero-activity starvation state, by construction (§1) and plausibly by
PDCP discard-timer masking (§2). An above-floor re-run with real scheduling
activity should produce a metric that actually responds to real conditions
again.

## GATE P0 verdict

**Stated plainly, as instructed**: for the specific failure mode M41/M42
found and confirmed structurally present in Paper #4's entire submitted
campaign, the compliance metric backing the submitted headline numbers is
**radio-insensitive by construction** — a fully-starved slice cannot be
distinguished from a genuinely healthy, lightly-loaded one using either of
this metric's two channels. This does not by itself prove the submitted
numbers ARE describing a starved run (that requires P1's live evidence) —
but it does mean **the compliance metric alone cannot be used to argue the
submitted campaign was healthy**, closing off "the numbers already show it
was fine" as a defense independent of a live re-run. Proceeding to P1 is
necessary, not optional, to determine what actually happened.
