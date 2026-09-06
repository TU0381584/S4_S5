# M44-C — GATE C interim report (urllc only; mmtc not yet run)

## Status: NOT PASSED as hypothesized. A THIRD measurement bug was found and fixed;
## the corrected data shows a hard cliff, not a graded shed region. Stopping here
## per GATED protocol — awaiting go before mmtc or any head-to-head scoping.

## 0. Two prior bugs, for context (already reported)
1. iperf3-target port-wedge silently killing traffic (M44-A) — fixed via container recreate + alive-check.
2. `INTERVAL_RE` treating iperf3's auto-scaled `Mbits/sec` as always-`Kbits/sec` (1000x under-report) — fixed by capturing the unit letter.

## 1. Third bug found this pass: zero-rate interval lines never matched

After fix #2, `sweep_urllc.jsonl` showed `served_kbps` staying flat (~3600→3409 Kbps)
across every ceiling ratio from 20% down to 4%, with `iperf_loss_pct=0.0` at *every*
step — including ratio=4%, where the independently-collected RLC AM instrumentation
(`M43DBG rlc_am_recv_sdu`, frozen-source-adjacent diagnostic, unchanged since M43)
reported **100% of SDUs rejected** at the RLC admission check
(`entity->tx_size + size > entity->tx_maxsize`). A slice whose RLC layer refuses
100% of new data cannot simultaneously be delivering ~95% of its offered
throughput at 0% loss — this is a direct contradiction, and neither reading was
invented; both come straight out of the two independent recording paths.

Root cause: `INTERVAL_RE` required a `[KMG]` unit-prefix letter on *both* the byte
count and the bitrate field. During a genuine, total, zero-throughput outage,
iperf3 prints the bare form with no prefix letter at all:

```
[  5] 314.00-315.00 sec  0.00 Bytes  0.00 bits/sec  0.225 ms  0/0 (0%)
```

`\wBytes` and `([KMG])bits/sec` both fail to match this line, so every truly-collapsed
interval was silently dropped from `rates[]`, and `parse_recent_intervals()`'s
fallback (`if not recent: recent = rates[-3:]`) returned the last interval it
*could* match — stale, pre-collapse, healthy-looking data. That is exactly the
flat ~3400-3600 Kbps / 0% loss pattern observed.

Also noted: iperf3's own per-interval loss% is `0/0 (0%)` when the receiver gets
*nothing* in that interval (no sequence numbers arrive to detect a gap against),
so even a fixed parser must not treat `loss_pct` as trustworthy proof of health
during a true outage — `served_kbps` vs. the row's own `offered_kbps` is the
signal to read.

Fix (both applied in `m44c_shed_sweep.py`, already committed-ready):
- `INTERVAL_RE`: made the unit-prefix group optional in both places (`\w?Bytes`, `([KMG]?)bits/sec`).
- `UNIT_TO_KBPS`: added `"": 0.001` (bare `bits/sec` → its own scale).

No new live run was needed to get corrected numbers for urllc — the already-captured
raw client log (`traffic_urllc_20260907_000423.log`) and gNB log
(`gnb_m41_20260907_000423.log`) were re-parsed offline with the fixed regex.

## 2. Corrected finding: a hard cliff, not a graded shed

Re-parsing the full raw traffic log (373 of 377 lines matched; the last line is a
mid-write truncation from process termination) into 10-second buckets of mean
received bitrate:

```
t=   0-220s   mean ≈ 3598-3602 Kbps   (flat, full health, every bucket)
t= 220-230s   mean = 2669 Kbps        (the one transitional bucket)
t= 230-380s   mean = 0.00 Kbps        (EVERY bucket, 146+ continuous seconds, no recovery)
```

Offered rate was a constant 3600 Kbps (12x native, self-calibrated from M44-A's
own demand curve) for the whole run. This is not a gradual roll-off: throughput is
essentially perfect for 220 seconds, crosses one 10-second transition bucket, then
drops to **exactly zero and never recovers** for the remainder of the captured log
— the process was still alive and printing (confirmed by the truncated final line)
when the sweep ended and `traffic_proc.terminate()` fired.

This is independently corroborated by the RLC AM instrumentation's own precisely
line-cursor-windowed per-ratio breakdown (not subject to any timestamp
reconstruction uncertainty):

| ratio | raw PRB | rlc_pct_rejected (in-window) | rlc_tx_size / tx_maxsize | buf_occ% |
|---|---|---|---|---|
| 20% | 21 | 0.0 | 9432 / 10,000,000 | 100.0 |
| 15% | 15 | 0.0 | 14672 / 10,000,000 | 75.0 |
| 12% | 12 | 0.0 | 9039 / 10,000,000 | 100.0 |
| 10% | 10 | 0.0 | 6943 / 10,000,000 | 87.5 |
| 9% | 9 | 0.0 | 10873 / 10,000,000 | 100.0 |
| **8%** | **8** | **43.2** | 9,999,885 / 10,000,000 | 100.0 |
| 7% | 7 | 100.0 | 9,999,885 / 10,000,000 | 100.0 |
| 6% | 6 | 100.0 | 9,999,885 / 10,000,000 | 100.0 |
| 5% | 5 | 100.0 | 9,999,885 / 10,000,000 | 100.0 |
| 4% | 4 | 100.0 | 9,999,885 / 10,000,000 | 100.0 |

`new_max_retx_events = 0` at every single step — this collapse produces **no**
max-RETX events. It is a different failure signature from the original M41 bug
(which manifested as catastrophic RLC max-RETX below the 5-PRB scheduler floor).
This one saturates the RLC AM transmit buffer (`tx_maxsize=10,000,000` bytes —
notably large for a bearer nominally carrying a "urllc" label) and then silently
rejects all new admissions at the door, with zero retransmission-limit signal to
the rest of the stack. It happens **above** the 5-PRB floor (at 7-8 raw PRB), so
it is not the same bug M41 fixed, and it would not have been caught by watching
for max-RETX events alone.

Both signals — the raw receiver-side outage and the RLC-side rejection curve —
agree on the shape: healthy through 9 raw PRB, a single ambiguous/transitional
point at 8 raw PRB, then total and sustained collapse at 7 raw PRB and below.
Reconstructing the exact epoch at which the raw-traffic collapse begins (the
client log carries only relative timestamps; an indirect anchor was built from an
ingress-rate discontinuity in the gNB log) places the transition in the
9%→8% boundary region, consistent with but not sharper than the RLC-side
breakdown — I am not claiming better precision than that; the RLC-side per-ratio
table above is the trustworthy version of "which ratio."

## 3. Answering GATE C's three questions

1. **Is there a monotone shed region above 5 PRB with no RLC collapse?** No. Above
   9 raw PRB there is no shed at all (perfect health). At 8 raw PRB there is a
   partial, transitional degradation (43% rejection, but tx_size not yet at
   its absolute logged ceiling). At 7 raw PRB and below — still above the 5-PRB
   scheduler floor — there is complete, sustained RLC admission collapse, not a
   graded reduction.
2. **How many distinguishable operating points exist?** Effectively two regimes
   and one transition point, not a spectrum: "fully healthy" (9-21 raw PRB, six
   tested points, statistically indistinguishable from each other) and "fully
   collapsed" (7-4 raw PRB, four tested points, also indistinguishable from each
   other — all zero throughput), joined by one ambiguous point at 8 raw PRB. This
   is much closer to the "binary served/collapsed snap" the milestone explicitly
   wanted to rule out than to a graded shed.
3. **How wide is the usable window in PRB, and does it hold for both slices?**
   For urllc: the transition is ~1 raw PRB wide (8 raw PRB is the only
   non-degenerate point), well short of what QoE-differentiated admission control
   would need. mmtc has not yet been tested with the corrected script — that is
   the natural next step but has not been run.

## 4. An open methodological question this run does NOT answer

This sweep ratchets the ceiling monotonically downward without ever resetting the
connection between steps, so the RLC AM transmit buffer carries state forward from
each higher-ceiling step into the next. The 8-raw-PRB step's `tx_size` was already
at 9,999,885/10,000,000 (99.999% full) — i.e., the buffer had already saturated by
the time 8 raw PRB was reached, most likely from backlog accumulated during the
9%-and-above steps at the now-lower ceiling. It is an open question, not yet
tested, whether 7-8 raw PRB collapses on its own from a **fresh** connection (cold
start at that ceiling, no inherited backlog), or whether the collapse is partly a
hysteresis artifact of this particular ratchet-down ordering. A fresh-restart-per-
ceiling-level variant, and/or a recovery check (raise the ceiling back up after
collapse and see if it un-sticks), would settle this and has not been run.

## 5. What has NOT been done yet
- mmtc has not been run with the twice-corrected script.
- No fresh-restart-per-level or recovery-check variant has been run (§4).
- No head-to-head DQN-QoE-vs-baseline scoping has been started, per the
  milestone's own explicit instruction to stop and await go.
