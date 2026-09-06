# M44-D — GATE D report: cold-start fixed-ceiling steady-state (urllc only)

## Verdict: GATE C's cliff was (mostly) a hysteresis artifact. A real, usable
## graded shed region exists between the 5-PRB scheduler floor and full
## health, entirely above the floor. DECISION BRANCH: stable points exist
## at 7-8 PRB cold -> proceed to validate on mmtc, then scope the DQN-QoE
## head-to-head in this band. STOPPING here per GATED protocol -- urllc
## only, mmtc not yet run, no head-to-head scoping started.

## 0. One bug found and fixed before trusting any data (4th, this project)

First attempt at ceiling=8 read `served_kbps=None`/`loss_pct=None` for the
first ~40s of the hold even though the RLC AM instrumentation showed real
traffic flowing (`rlc_entity_calls_in_window` growing normally). The raw
traffic log was **completely empty** at that point. Cause: iperf3's stdout,
redirected to a file (not a TTY), is fully block-buffered by libc -- GATE
C's own sampling cadence had a long (~55s) lead-in before its first parse
call, long enough for a flush to have already happened by chance; this
milestone's tighter ~15s-to-first-sample cadence exposed the underlying
buffering delay directly. Fixed by wrapping the iperf3 invocation in
`stdbuf -oL -eL` (forces line-buffered stdout via LD_PRELOAD) in
`m44c_shed_sweep.py`'s `launch_reporting_traffic()`, shared by both GATE C
and this milestone. Verified with a 6-second smoke test (lines appeared
within 3s) before discarding the first attempt's run and restarting the
full 5-ceiling sweep from scratch. No config or frozen source touched;
`tx_maxsize` untouched, as instructed.

## 1. Protocol actually run

Randomized order (seed 44004): **8, 7, 9, 10, 6** raw PRB. Each ceiling got
its own full cold start: contention gate on a throwaway stack instance,
`docker compose down/up` + fresh gNB/UE bring-up, ceiling set to the fixed
target value BEFORE any urllc traffic existed on the connection, an explicit
`dl_mac_buffer_occupation` poll confirming ~0% before traffic started, then
the SAME offered load as GATE C (12x native = 3600 Kbps) held for >=120s
(8 samples every ~15s wall-clock-plus-overhead, actually running ~163-172s
per ceiling once per-sample KPM/log-read overhead is included). Buffer was
confirmed drained (0.0%) before traffic at every single one of the 5 runs.
Zero `new_max_retx_events` across all 40 samples, all 5 ceilings.

## 2. Full per-ceiling trajectory (all 8 samples)

| ceiling | t=15s | t=35s | t=56s | t=77s | t=98s | t=120s | t=142s | t=163s |
|---|---|---|---|---|---|---|---|---|
| 10 | 3601/0/0 | 3600/0/0 | 3601/0/0 | 3599/0/0 | 3599/0/0 | 3600/0/0 | 3599/0/0 | 3600/0/0 |
| 9  | 3600/0/0 | 3601/0/0 | 3599/0/0 | 3601/0/0 | 3601/0/0 | 3599/0/0 | 3599/0/0 | 3600/0/0 |
| 8  | 3620/0/0 | 3599/0/0 | 3623/0/0 | 3679/0/0 | 3602/0/0 | 3553/0/0 | 3699/0/0 | 3716/0/0 |
| 7  | 3407/0/0 | 3346/0/0 | 3398/0/0 | 3358/0/0 | 3385/0/0 | 3370/0/0 | 3397/0/0 | 3386/0/0 |
| 6  | 2623/0/0 | 2609/0/0 | 2656/0/0 | 2574/0/25 | 1681/37/44 | 2324/44/35 | 2291/37/34 | 2165/39/37 |

(cell format: served_kbps / iperf_loss_pct / rlc_pct_rejected_in_window)

Steady-state summary (mean +/- population stdev, last 4 of 8 samples):

| ceiling (raw PRB) | served_kbps | loss_pct | rlc_rejected_pct | new_max_retx (whole run) |
|---|---|---|---|---|
| 10 | 3599.7 +/- 0.3 | 0.00 +/- 0.00 | 0.00 +/- 0.00 | 0 |
| 9  | 3600.0 +/- 0.8 | 0.00 +/- 0.00 | 0.00 +/- 0.00 | 0 |
| 8  | 3642.3 +/- 67.7 | 0.00 +/- 0.00 | 0.00 +/- 0.00 | 0 |
| 7  | 3384.4 +/- 9.6  | 0.00 +/- 0.00 | 0.00 +/- 0.00 | 0 |
| 6  | 2115.2 +/- 257.8 | 39.31 +/- 2.89 | 37.45 +/- 3.86 | 0 |

Offered load was a constant 3600 Kbps throughout, identical to GATE C.

## 3. Answering GATE D's three questions

**1. At each of 6/7/8 PRB cold, does the slice reach a STABLE served state, or collapse regardless of history?**

7 and 8 PRB: yes, fully stable, and fully healthy -- tight variance
(stdev 0.3-68 out of ~3600, i.e. <2%), exactly 0% loss and 0% RLC
rejection for the entire ~165s hold, zero RETX events. 8 PRB's mean is
technically ~1% above the offered rate, well within normal CBR-generator
sampling noise (GATE C's own healthy ratios showed the same +/-1%
wobble).

6 PRB: reaches a stable state, but not a healthy one. It is NOT a
collapse (never approaches 100% rejection or zero throughput, and never
produces a single max-RETX event across the whole run) -- it settles into
a bounded, noisy-but-non-degrading partial-service state: ~2100 Kbps
served (~59% of offered), ~39% real packet loss, ~37% RLC admission
rejection, all roughly flat (not trending toward either extreme) over
the last ~70s of the hold.

Notably, 6 PRB was NOT degraded from the very start: it read fully clean
(0% loss, 0% rejection, ~2600-2650 Kbps served -- itself already ~27%
short of offered, so under-capacity from the first sample) for the first
~56-78 seconds, only crossing into the partial-rejection/partial-loss
regime around t=78-100s. A hold shorter than that would have
under-estimated 6 PRB's true steady-state severity -- this validates the
milestone's own choice of a >=120s minimum hold rather than a shorter one.

**2. Does any stable, distinguishable operating point exist between the 5-PRB floor and ~9-PRB full health -- i.e. is there ANY graded shed region once hysteresis is removed?**

Yes. Three distinguishable, stable regimes were found, all above the
5-PRB scheduler floor:
- **8-10 raw PRB**: full health, statistically indistinguishable from each other.
- **7 raw PRB**: full health in every measured respect (0% loss, 0% rejection, zero RETX) but with a small, real, and stable ~6% throughput shortfall against offered (3384 vs 3600) -- a genuine, reproducible, mild degradation point distinct from both full health and the 6-PRB regime.
- **6 raw PRB**: a substantially larger but still bounded degradation (~40% shortfall, ~39% real loss, ~37% rejection), stable rather than collapsing.

That is a real, three-point graded shed band, not the binary
served/collapsed snap GATE C reported.

**3. How does the cold-start curve differ from GATE C's ratchet curve (isolates the hysteresis contribution)?**

| raw PRB | GATE C (ratcheted, steady value) | M44-D (cold, steady-state mean) | hysteresis contribution |
|---|---|---|---|
| 9 | 0% rejected, full throughput | 0% rejected, full throughput | none -- never near the transition |
| 8 | 43.2% rejected (partial) | 0% rejected, full throughput | **100% of the degradation at 8 PRB was a ratchet artifact** |
| 7 | 100% rejected, 0 throughput, permanent, no recovery in 146+s | 0% rejected, 3384 Kbps (94% of offered), stable 165s | **the entire collapse at 7 PRB was a ratchet artifact** -- 7 PRB does not self-collapse from cold |
| 6 | 100% rejected, 0 throughput (part of the same post-collapse plateau) | ~37% rejected, ~2115 Kbps, bounded, non-collapsing | hysteresis converts a real-but-moderate degradation into a total, unrecovering outage |

GATE C's ratchet-down methodology was not just inflating the severity at
the single ambiguous point (8 PRB) -- it was producing a qualitatively
wrong answer (permanent total collapse) at every point it tested at or
below the true transition, including 7 and 6 raw PRB, both of which have
real, bounded, non-collapsing steady states on their own.

## 4. Decision

Per the milestone's own decision tree: **stable points exist at 7-8 PRB
cold.** GATE C's cliff was a sweep artifact of the monotonic ratchet-down
methodology (inherited RLC AM buffer backlog compounding across
descending steps), not a steady-state property of the ceiling surface.
A real, usable, three-point graded shed band exists between the 5-PRB
scheduler floor and full health (6 PRB: bounded partial service; 7 PRB:
near-full with a small stable shortfall; 8+ PRB: full health) --
entirely reachable without ratcheting, i.e. from a genuine cold
admission decision, which is the actual operating regime an admission
controller would use.

Per the milestone's explicit instruction, this branch means: **proceed to
validate on mmtc, then scope the DQN-QoE-vs-baseline campaign in this
band** -- but per the same instruction ("STOP after urllc. Do not run
mmtc or scope the head-to-head until D's branch is known"), neither of
those has been started. Reporting now and awaiting go.

## 5. What has NOT been done yet
- mmtc has not been tested at all under this cold-start protocol.
- No head-to-head DQN-QoE-vs-baseline scoping has been started.
- The ~60-100s onset time for 6 PRB's transition into its degraded
  steady state has not been further characterized (e.g. whether it is
  sensitive to offered load, or has its own dependence on exact PRB
  count) -- noted as an open detail, not investigated further here.
