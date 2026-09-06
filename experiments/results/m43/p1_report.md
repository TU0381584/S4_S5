# M43-P1: does the SUBMITTED Paper #4 config fail live under its own harness?

Live test. Standing constraints honored: no edits to any committed
config/result/frozen source (the submitted `saclb_campaign_v2.yaml` and the
DQN-QoE checkpoint were used byte-identical, confirmed via `git diff` against
HEAD before the run and pinned at git tag `m43-p1-submission-record`); new
instrumentation added only to ORANSlice C source (gitignored, same class of
change as M41's diagnostic instrumentation, not a "committed config/result");
new traffic launcher (`experiments/scripts/m43_launch_original_traffic.sh`)
is a new file, reproduces `experiments/configs/traffic_profiles.yaml`'s exact
spec, does not touch any existing script; contention gate run before the live
measurement; netns recreated as part of `restart_ran_stack.sh`'s own
idempotent bring-up; results under `experiments/results/m43/`, never written
into the original campaign's directories.

## Setup

- Config: `experiments/configs/saclb_campaign_v2.yaml` (unmodified, confirmed
  byte-identical to the submitted state).
- Checkpoint: the actual submitted DQN-QoE checkpoint
  (`experiments/results/offline_v2/qoe/seed256/dqn/offline_closed_loop/rep_0/checkpoint.pt`,
  confirmed byte-identical).
- Harness: `experiments/scripts/run_live_eval_arm.py` (unmodified, the
  original evaluation orchestrator) invoking
  `framework/qoe_oran_framework/xapp/saclb_xapp.py` (unmodified) directly —
  NOT `m41_envelope_sweep.py`'s own iperf3 harness.
- Traffic: `experiments/scripts/m43_launch_original_traffic.sh` (new),
  reproducing `traffic_profiles.yaml` exactly (embb 4M/1200B sustained,
  urllc 300K/100B sustained, mmtc 50K/80B bursty 2s-on/6s-off).
- 2 episodes (one batch, `--episodes-total 2 --batch-size 2`), fresh seed
  43003 (not one of the original campaign's 950-977, per "never reuse old-rig
  data").
- New instrumentation added for this milestone (ORANSlice C source,
  gitignored, diff preserved in `docs/patches/m41_diagnostic_instrumentation.patch`):
  - `nr_pdcp_entity.c`: `M43DBG pdcp_ingress` at `process_sdu()` entry
    (rb_id, size, cumulative rxsdu_pkts/bytes).
  - `nr_rlc_oai_api.c`: `M43DBG rlc_ingress` at `rlc_data_req()`, DL-direction
    only (rnti, rb_id, size) — logs what PDCP handed down to RLC.
  - `nr_rlc_entity_am.c`: `M43DBG rlc_am_recv_sdu` at the entity's own
    `recv_sdu()`, logging `tx_size`/`tx_maxsize`/`sdu_rejected` and whether
    THIS specific SDU was rejected — the real, active bounded-buffer drop
    mechanism (see note on the PDCP `discard_timer` correction below).

**Correction to P0's own hypothesis, found before this run**: further source
reading found PDCP's `discard_timer` is configured
(`nr_pdcp_oai_api.c:848,1171`) but **never actually checked or enforced
anywhere in `nr_pdcp_entity.c`** — it is dead code in this fork, not an
active drop mechanism. The real, active drop point is RLC AM's own
`recv_sdu()` (`nr_rlc_entity_am.c:1783`): `if (entity->tx_size + size >
entity->tx_maxsize) { entity->sdu_rejected++; return; }` — a genuine bounded
transmission buffer that silently discards SDUs once full. This is what got
instrumented instead.

## Result

**RLC max-RETX fires, in large numbers, on all three slices** —
`ue1`(embb): 9,266 events; `ue2`(mmtc): 11,187 events; `ue3`(urllc): 10,293
events, over the 600s run.

**The recomputed compliance metric reflects this failure directly** (does
NOT mask it): `mean_sla_viol: 1.0` (every step in violation),
`sla_margin_by_slice: {embb: -965124.06, urllc: -836518.95, mmtc: -1740.78}`.
Notably, `embb`'s episode-2 margin (`-1,002,377.5`) matches M8's own
historical documented figure **to the decimal** — strong evidence this is a
real, reproducible saturation dynamic of this rig's telemetry under genuine
sustained starvation, not a one-off artifact.

**Mechanism, confirmed directly by the new instrumentation**:
- PDCP → RLC handoff: `pdcp_ingress` (708,274), `rlc_ingress` (708,494),
  `rlc_am_recv_sdu` (708,669) calls — all within noise of each other. PDCP
  drops nothing (confirmed: `process_sdu()` has no drop logic at all).
- **RLC's own bounded buffer silently rejected 488,717 of 708,669 SDUs
  (≈69%)** — `rejected_this_sdu=1` in the instrumentation. This is real,
  active, massive data loss happening entirely inside RLC, invisible to
  PDCP-side counters.
- The recorded live ceilings show why: this run's specific decision
  trajectory walked all three slices down to `(min=1,max=1)` — the absolute
  floor — within the first few steps and stayed there for nearly the entire
  run (spot-checked at steps 0,1,2,5,10,61,-3,-2: floor-pinned throughout
  except one brief step-61 excursion). At 1 raw PRB, `pf_dl_slice()`'s
  scheduling loop never executes (M41's confirmed mechanism), so RLC's
  transmit buffer never drains and fills to `tx_maxsize` almost immediately.
- Cross-checked against the existing M41DBG per-slot instrumentation: mmtc
  (sid=2) shows 73,791/74,080 samples (99.6%) at `min_prbs=0` — essentially
  total, sustained zero-grant starvation for the entire run. embb/urllc show
  a similar majority-zero pattern (~92-93%) with brief nonzero windows.
- `dl_mac_buffer_occupation`'s fallback (`limitation: "...was 0 for all
  UEs..."`) fired in only 1 of 122 steps (the very first, before backlog had
  time to build) — confirming the REAL buffer-occupancy telemetry was live
  and populated for this run, not the degraded proxy P0 found in the
  original campaign's logs.

## GATE P1 classification

**Branch 2: RLC max-RETX fires AND the proxy reflects it.** Neither branch 1
(metric masks failure) nor branch 3 (ceiling inert, no failure) applies here
— this run shows a real, severe, correctly-detected failure. Per the
milestone's own framing: **a submitted run that behaved like this one would
have shown catastrophic violation, not the reported 100/100/100 DQN-QoE
compliance.** This specific fresh run's numbers do not match a clean
submitted run.

## What this does and doesn't establish

**Established**: the exact submitted config, checkpoint, and traffic
specification, run live under the exact original harness, CAN and DID
produce catastrophic real RLC failure that the paper's own metric correctly
flags as total violation — settling P0's own open question about whether an
above-floor-sensitive-when-triggered metric would show real state (it does).
The PDCP-vs-RLC mechanism question P0 flagged is also settled: PDCP's
discard_timer is inert; RLC's own bounded buffer is the real, confirmed,
actively-firing drop point.

**NOT yet established**: whether this is what actually happened during the
28 seeds (950-977) the submitted campaign actually used. This run's ceiling
trajectory (pinned at floor almost immediately) diverged sharply from the
one historical sample checked in M42 (seed 961, which rode urllc/mmtc UP
toward their caps instead) — consistent with genuine seed-dependent policy
variance (the DQN-QoE policy's decisions are a function of a seeded
synthetic-arrival stream, so different seeds can plausibly produce very
different accept/reject trajectories against the same checkpoint). Whether
seed 43003's floor-pinning trajectory is typical, or an unlucky outlier
relative to the actual submitted seeds, is open — resolving it would need
re-running with (or statistically characterizing) the actual submitted
seed set, not decided here.

## Manifest

See `experiments/results/m43/manifest.csv` (P1 rows) for the full
step-by-step trace, including the two operational retries (wrong Python
interpreter in the harness's own subprocess call — a pre-existing bug in
`run_live_eval_arm.py`'s reliance on bare `python3` resolving correctly from
PATH, not `sys.executable`; and a relative-path issue from the harness's
`cwd=FRAMEWORK_DIR` subprocess launch) neither of which touched the rig
bring-up or traffic, confirmed via `health_check.sh`'s own healthy reports
throughout.
