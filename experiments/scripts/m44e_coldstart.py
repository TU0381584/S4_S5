#!/usr/bin/env python3
"""M44-E: cold-start graded-band characterization, generalized across slices.

Extends M44-D's cold-start methodology (ceiling fixed from the first
packet -- never wide-open, never ratcheted -- buffer confirmed drained
before traffic, >=120s hold, spaced/randomized ceiling order, contention
gate before every live run) to mmtc (E1) and, later, embb (E2). E1/E2 each
answer: does a graded shed band exist above the 5-PRB scheduler floor for
this slice, how many distinguishable stable points, at what raw-PRB range
and offered load. E3 (separate, after E1+E2 are both reported and a go is
given) asks whether any single regime puts multiple slices in their bands
at once.

Reuses m44c_shed_sweep.py's corrected parsers unmodified (bare-"0.00"
throughput regex, stdbuf -oL line buffering already baked into its
launch_reporting_traffic -- duplicated here as launch_traffic() only
because that function does an internal SLICE_TRAFFIC[slice_id] lookup
that doesn't have an "embb" entry; behavior is otherwise identical) and
the M43DBG RLC AM instrumentation via parse_rlc_am_stats/busiest_entity,
not avg_prbs_dl. Never touches min_rbSize, tx_maxsize, or committed
config/frozen source. New logic and configs only. Writes to
experiments/results/m44e/ only.
"""
import argparse
import json
import random
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m41_envelope_sweep as m41
import m44_scarcity_probe as m44a
import m44c_shed_sweep as m44c

RIG = m41.RIG
OUT_DIR = RIG / "experiments/results/m44e"

# m44a.SLICE_TRAFFIC only carries urllc/mmtc (M44-A never targeted embb,
# since it clears the floor natively) -- extended here, in this new
# script's own namespace only, for E2.
SLICE_INFO = dict(m44a.SLICE_TRAFFIC)
SLICE_INFO["embb"] = {"port": 5201, "packet_len": 1200, "sd": 16777215, "native_bitrate_kbps": 4000}

UE_LOG_NAME = {"urllc": "ue3", "mmtc": "ue2", "embb": "ue1"}

DEFAULT_CEILINGS = {"mmtc": [5, 6, 7, 8, 9], "embb": None}
# mmtc: M44-A's own measured demand at 50x/2.5Mbps is ~7.07 raw PRB, just
# above the 5-PRB floor -- per this milestone's explicit instruction.
DEFAULT_OFFERED_MULT = {"mmtc": 50.0, "embb": None}
ORDER_SEED = {"mmtc": 44006, "embb": 44007}
HOLD_S = 120.0
SAMPLE_INTERVAL_S = 15.0


def launch_traffic(slice_id: str, bitrate_kbps: float, ue_ip: str, ns: str | None,
                    log_path: Path) -> subprocess.Popen:
    """Same as m44c_shed_sweep.launch_reporting_traffic (stdbuf-wrapped,
    -i 1, --reverse), duplicated only because that function's internal
    SLICE_TRAFFIC lookup has no "embb" entry -- reads from this script's
    own SLICE_INFO instead."""
    info = SLICE_INFO[slice_id]
    prefix = f"sudo ip netns exec {ns} " if ns else "sudo "
    cmd = (f"{prefix}stdbuf -oL -eL iperf3 -c {m44a.TARGET_CONTAINER_IP} -p {info['port']} -B {ue_ip} "
           f"-u -b {bitrate_kbps}K -l {info['packet_len']} --reverse -i 1 -t 3600")
    fh = open(log_path, "w")
    proc = subprocess.Popen(cmd, shell=True, stdout=fh, stderr=subprocess.STDOUT)
    time.sleep(2)
    return proc


def confirm_buffer_drained(sd: int, label: str) -> float | None:
    demand = m44a.poll_demand(polls=3, interval_s=1.0)
    m = re.search(rf"sst1/sd{sd}[^\n]*dl_mac_buffer_occupation=\s*([\d.]+)%", demand["stdout"])
    pct = float(m.group(1)) if m else None
    print(f"[m44e] [{label}] dl_mac_buffer_occupation for sst1/sd{sd} = {pct}%", file=sys.stderr)
    return pct


def run_one_ceiling(slice_id: str, ceiling: int, bitrate: float, run_idx: int, total: int) -> dict:
    info = SLICE_INFO[slice_id]
    ts = time.strftime("%Y%m%d_%H%M%S")
    print(f"[m44e] === run {run_idx}/{total}: COLD START slice={slice_id} ceiling={ceiling} raw PRB "
          f"(offered={bitrate}Kbps) ===", file=sys.stderr)

    if not m41.ensure_docker_core(force_fresh=True):
        print("[m44e] FATAL: docker core failed (phase 1)", file=sys.stderr)
        return {"slice": slice_id, "ceiling": ceiling, "error": "docker_core_failed_phase1"}
    if not m41.restart_native_stack(ts):
        m41.teardown(None, ts)
        return {"slice": slice_id, "ceiling": ceiling, "error": "bringup_failed_gate_phase"}
    m41.start_traffic(1.0, ts)
    print("[m44e] gate-phase traffic launched, 30s pre-gate stabilization...", file=sys.stderr)
    time.sleep(30)
    gate_ok = m41.run_contention_gate(ts)
    print(f"[m44e] gate: {'PASS' if gate_ok else 'FAIL'}", file=sys.stderr)
    m41.teardown(None, ts)
    if not gate_ok:
        return {"slice": slice_id, "ceiling": ceiling, "error": "gate_failed"}

    if not m41.ensure_docker_core(force_fresh=True):
        return {"slice": slice_id, "ceiling": ceiling, "error": "docker_core_failed_phase2"}
    ts2 = time.strftime("%Y%m%d_%H%M%S")
    if not m41.restart_native_stack(ts2):
        m41.teardown(None, ts2)
        return {"slice": slice_id, "ceiling": ceiling, "error": "bringup_failed_phase2"}

    m44c.set_ceiling(1, info["sd"], ceiling, ceiling)
    time.sleep(3)
    pre_buf_pct = confirm_buffer_drained(info["sd"], "pre-traffic (expect ~0, fresh RLC entity)")

    ue_ip, ns = m44a.get_ue_ip(slice_id)
    m41.start_traffic(1.0, ts2)
    time.sleep(2)
    m41.pkill_pattern(f"iperf3 -c 172.22.0.50 -p {info['port']}")
    time.sleep(2)
    m44a.recreate_iperf3_target()

    traffic_log = OUT_DIR / f"traffic_{slice_id}_ceil{ceiling}_{ts2}.log"
    traffic_proc = launch_traffic(slice_id, bitrate, ue_ip, ns, traffic_log)
    if traffic_proc.poll() is not None:
        print("[m44e] FATAL: traffic client failed to start", file=sys.stderr)
        m41.teardown(None, ts2)
        return {"slice": slice_id, "ceiling": ceiling, "error": "traffic_launch_failed"}

    gnb_log = RIG / f"experiments/logs/gnb_m41_{ts2}.log"
    ue_log = RIG / f"experiments/logs/{UE_LOG_NAME[slice_id]}_m41_{ts2}.log"
    retx_seen: dict = {}
    m41.tail_new_retx(ue_log, retx_seen)

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
                "slice": slice_id, "ceiling_raw_prbs": ceiling, "sample_idx": i,
                "elapsed_s": round(elapsed, 1),
                "served_kbps": thr["mean_kbps"], "offered_kbps": bitrate,
                "iperf_loss_pct": thr["mean_loss_pct"],
                "rlc_entity_calls_in_window": busiest["n"], "rlc_pct_rejected_in_window": pct_rejected,
                "rlc_tx_size": busiest["last_tx_size"], "rlc_tx_maxsize": busiest["last_tx_maxsize"],
                "dl_mac_buffer_occupation_pct": buf_occ_pct,
                "new_max_retx_events": new_retx,
                "pre_traffic_buffer_drained_pct": pre_buf_pct,
            }
            samples.append(row)
            (OUT_DIR / f"trajectory_{slice_id}_ceil{ceiling}.jsonl").open("a").write(json.dumps(row) + "\n")
            print(f"[m44e]   [{slice_id} ceiling={ceiling} t={elapsed:.0f}s] served={thr['mean_kbps']}Kbps "
                  f"loss={thr['mean_loss_pct']}% rlc_rejected%={pct_rejected} buf_occ%={buf_occ_pct} "
                  f"new_retx={new_retx}", file=sys.stderr)

            if new_retx > 50:
                print(f"[m44e] COLLAPSE ({new_retx} new max-RETX) at {slice_id} ceiling={ceiling}, "
                      f"stopping this run", file=sys.stderr)
                aborted = True
                break
    finally:
        traffic_proc.terminate()
        m41.teardown(None, ts2)

    return {"slice": slice_id, "ceiling": ceiling, "pre_traffic_buffer_drained_pct": pre_buf_pct,
            "samples": samples, "aborted": aborted, "ts2": ts2}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slice", required=True, choices=["mmtc", "embb"])
    ap.add_argument("--ceilings", type=int, nargs="+", default=None)
    ap.add_argument("--offered-mult", type=float, default=None)
    args = ap.parse_args()

    ceilings = args.ceilings or DEFAULT_CEILINGS[args.slice]
    offered_mult = args.offered_mult if args.offered_mult is not None else DEFAULT_OFFERED_MULT[args.slice]
    if ceilings is None or offered_mult is None:
        print(f"[m44e] FATAL: no default ceilings/offered-mult configured yet for slice={args.slice} "
              f"-- pass --ceilings and --offered-mult explicitly (TODO(MEASURE): not yet scoped)",
              file=sys.stderr)
        return 1

    info = SLICE_INFO[args.slice]
    bitrate = info["native_bitrate_kbps"] * offered_mult

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    order = ceilings[:]
    random.Random(ORDER_SEED[args.slice]).shuffle(order)
    print(f"[m44e] === M44-E cold-start probe: slice={args.slice}, ceilings={ceilings}, "
          f"offered={bitrate}Kbps ({offered_mult}x native), randomized order "
          f"(seed={ORDER_SEED[args.slice]}) = {order} ===", file=sys.stderr)

    all_results = []
    for idx, ceiling in enumerate(order, 1):
        result = run_one_ceiling(args.slice, ceiling, bitrate, idx, len(order))
        all_results.append(result)
        (OUT_DIR / f"all_runs_{args.slice}.json").write_text(json.dumps(all_results, indent=2))

    print(f"[m44e] === DONE, slice={args.slice}, {len(all_results)} ceilings tested, "
          f"results in {OUT_DIR} ===", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
