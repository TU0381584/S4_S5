#!/usr/bin/env python3
"""M44-D: cold-start fixed-ceiling steady-state probe for urllc.

GATE C found a hard served/collapsed cliff at 7-9 raw PRB via a monotonic
ratchet-down sweep (wide-open ceiling, then decreasing steps, all on one
continuous connection). That sweep design means each step's RLC AM tx
buffer inherits backlog from the PREVIOUS, higher-ceiling step -- so the
observed cliff could be a hysteresis artifact of ratcheting down, not a
steady-state property of the ceiling surface itself.

M44-D isolates that: for each of {6,7,8,9,10} raw PRB, tear the whole
stack down and bring it back up completely fresh, set the ceiling to that
FIXED value BEFORE any urllc traffic exists on the new connection (so the
RLC AM entity is created empty, already capped at the target ceiling --
never wide-open even transiently, never ratcheted), explicitly confirm
the buffer reads drained, then hold the SAME offered load as GATE C
(12x native / 3600Kbps, identical calibration) for >=120s, sampling
served throughput/loss (the corrected parser, not iperf3's own possibly-
misleading loss%), RLC AM SDU-reject%, buffer occupancy and max-RETX
about every 15s -- the full trajectory, not just an endpoint, since a
"still collapsing at t=120s" curve and a "flat and healthy by t=30s"
curve both look like "no new RETX events" if you only check the end.

Ceiling order is a fixed pseudorandom permutation (seed 44004), not the
monotonic 10->4 order GATE C used, specifically so no two runs share GATE
C's own descending adjacency by coincidence.

Never touches min_rbSize, tx_maxsize, or committed config/frozen source.
Reuses m41_envelope_sweep.py / m44_scarcity_probe.py / m44c_shed_sweep.py
unmodified (import only). New logic and configs only. Writes to
experiments/results/m44d/ only.
"""
import json
import random
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m41_envelope_sweep as m41
import m44_scarcity_probe as m44a
import m44c_shed_sweep as m44c

RIG = m41.RIG
OUT_DIR = RIG / "experiments/results/m44d"

SLICE_ID = "urllc"
CEILINGS = [6, 7, 8, 9, 10]
ORDER_SEED = 44004
HOLD_S = 120.0
SAMPLE_INTERVAL_S = 15.0
OFFERED_MULT = m44c.CALIBRATED_MULT["urllc"]  # 12.0x native = 3600Kbps -- identical offered load to GATE C


def confirm_buffer_drained(sd: int, label: str) -> float | None:
    """Polls KPM once and returns dl_mac_buffer_occupation% for sst1/sd{sd}.
    This is the milestone's own required 'verify drained buffer at each
    start' check -- logged explicitly either way, not assumed from a fresh
    restart alone."""
    demand = m44a.poll_demand(polls=3, interval_s=1.0)
    m = re.search(rf"sst1/sd{sd}[^\n]*dl_mac_buffer_occupation=\s*([\d.]+)%", demand["stdout"])
    pct = float(m.group(1)) if m else None
    print(f"[m44d] [{label}] dl_mac_buffer_occupation for sst1/sd{sd} = {pct}%", file=sys.stderr)
    return pct


def run_one_ceiling(ceiling: int, run_idx: int, total: int) -> dict:
    info = m44a.SLICE_TRAFFIC[SLICE_ID]
    bitrate = info["native_bitrate_kbps"] * OFFERED_MULT
    ts = time.strftime("%Y%m%d_%H%M%S")
    print(f"[m44d] === run {run_idx}/{total}: COLD START ceiling={ceiling} raw PRB "
          f"(offered={bitrate}Kbps) ===", file=sys.stderr)

    # Phase 1: contention gate on a throwaway stack instance (standing
    # constraint: gate before every live run).
    if not m41.ensure_docker_core(force_fresh=True):
        print("[m44d] FATAL: docker core failed (phase 1)", file=sys.stderr)
        return {"ceiling": ceiling, "error": "docker_core_failed_phase1"}
    if not m41.restart_native_stack(ts):
        m41.teardown(None, ts)
        return {"ceiling": ceiling, "error": "bringup_failed_gate_phase"}
    m41.start_traffic(1.0, ts)
    print("[m44d] gate-phase traffic launched, 30s pre-gate stabilization...", file=sys.stderr)
    time.sleep(30)
    gate_ok = m41.run_contention_gate(ts)
    print(f"[m44d] gate: {'PASS' if gate_ok else 'FAIL'}", file=sys.stderr)
    m41.teardown(None, ts)
    if not gate_ok:
        return {"ceiling": ceiling, "error": "gate_failed"}

    # Phase 2: a genuinely fresh stack for the actual cold-start measurement.
    if not m41.ensure_docker_core(force_fresh=True):
        return {"ceiling": ceiling, "error": "docker_core_failed_phase2"}
    ts2 = time.strftime("%Y%m%d_%H%M%S")
    if not m41.restart_native_stack(ts2):
        m41.teardown(None, ts2)
        return {"ceiling": ceiling, "error": "bringup_failed_phase2"}

    # Ceiling fixed BEFORE any traffic of any kind exists on this stack --
    # never wide-open, never ratcheted down from a higher value. This is
    # the entire point of the milestone: isolate steady-state from hysteresis.
    m44c.set_ceiling(1, info["sd"], ceiling, ceiling)
    time.sleep(3)
    pre_buf_pct = confirm_buffer_drained(info["sd"], "pre-traffic (expect ~0, fresh RLC entity)")

    ue_ip, ns = m44a.get_ue_ip(SLICE_ID)
    m41.start_traffic(1.0, ts2)  # native background for embb/mmtc (contention) + urllc (replaced next)
    time.sleep(2)
    m41.pkill_pattern(f"iperf3 -c 172.22.0.50 -p {info['port']}")
    time.sleep(2)
    m44a.recreate_iperf3_target()

    traffic_log = OUT_DIR / f"traffic_urllc_ceil{ceiling}_{ts2}.log"
    traffic_proc = m44c.launch_reporting_traffic(SLICE_ID, bitrate, ue_ip, ns, traffic_log)
    if traffic_proc.poll() is not None:
        print("[m44d] FATAL: traffic client failed to start", file=sys.stderr)
        m41.teardown(None, ts2)
        return {"ceiling": ceiling, "error": "traffic_launch_failed"}

    gnb_log = RIG / f"experiments/logs/gnb_m41_{ts2}.log"
    ue_log = RIG / f"experiments/logs/ue3_m41_{ts2}.log"
    retx_seen: dict = {}
    m41.tail_new_retx(ue_log, retx_seen)  # prime baseline (expect 0 on a fresh log)

    samples = []
    gnb_line_cursor = len(gnb_log.read_text(errors="ignore").splitlines()) if gnb_log.exists() else 0
    t0 = time.time()
    aborted = False
    try:
        n_samples = int(HOLD_S // SAMPLE_INTERVAL_S)
        for i in range(n_samples):
            time.sleep(SAMPLE_INTERVAL_S)
            elapsed = time.time() - t0

            thr = m44c.parse_recent_intervals(traffic_log, SAMPLE_INTERVAL_S)
            rlc = m44c.parse_rlc_am_stats(gnb_log, gnb_line_cursor)
            gnb_line_cursor = rlc["next_line"]
            busiest = m44c.busiest_entity(rlc["entities"])
            pct_rejected = (100.0 * busiest["n_rejected"] / busiest["n"]) if busiest["n"] else None

            demand_now = m44a.poll_demand(polls=3, interval_s=1.0)
            buf_m = re.search(rf"sst1/sd{info['sd']}[^\n]*dl_mac_buffer_occupation=\s*([\d.]+)%",
                               demand_now["stdout"])
            buf_occ_pct = float(buf_m.group(1)) if buf_m else None

            new_retx = m41.tail_new_retx(ue_log, retx_seen)

            row = {
                "ceiling_raw_prbs": ceiling, "sample_idx": i, "elapsed_s": round(elapsed, 1),
                "served_kbps": thr["mean_kbps"], "offered_kbps": bitrate,
                "iperf_loss_pct": thr["mean_loss_pct"],
                "rlc_entity_calls_in_window": busiest["n"], "rlc_pct_rejected_in_window": pct_rejected,
                "rlc_tx_size": busiest["last_tx_size"], "rlc_tx_maxsize": busiest["last_tx_maxsize"],
                "dl_mac_buffer_occupation_pct": buf_occ_pct,
                "new_max_retx_events": new_retx,
                "pre_traffic_buffer_drained_pct": pre_buf_pct,
            }
            samples.append(row)
            (OUT_DIR / f"trajectory_ceil{ceiling}.jsonl").open("a").write(json.dumps(row) + "\n")
            print(f"[m44d]   [ceiling={ceiling} t={elapsed:.0f}s] served={thr['mean_kbps']}Kbps "
                  f"loss={thr['mean_loss_pct']}% rlc_rejected%={pct_rejected} buf_occ%={buf_occ_pct} "
                  f"new_retx={new_retx}", file=sys.stderr)

            if new_retx > 50:
                print(f"[m44d] COLLAPSE ({new_retx} new max-RETX) at ceiling={ceiling}, "
                      f"stopping this run", file=sys.stderr)
                aborted = True
                break
    finally:
        traffic_proc.terminate()
        m41.teardown(None, ts2)

    return {"ceiling": ceiling, "pre_traffic_buffer_drained_pct": pre_buf_pct,
            "samples": samples, "aborted": aborted, "ts2": ts2}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    order = CEILINGS[:]
    random.Random(ORDER_SEED).shuffle(order)
    print(f"[m44d] === M44-D cold-start fixed-ceiling probe: urllc, ceilings={CEILINGS}, "
          f"randomized order (seed={ORDER_SEED}) = {order} ===", file=sys.stderr)

    all_results = []
    for idx, ceiling in enumerate(order, 1):
        result = run_one_ceiling(ceiling, idx, len(order))
        all_results.append(result)
        (OUT_DIR / "all_runs.json").write_text(json.dumps(all_results, indent=2))

    print(f"[m44d] === DONE, {len(all_results)} ceilings tested, results in {OUT_DIR} ===",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
