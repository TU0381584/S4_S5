#!/usr/bin/env python3
"""M44-E2b step 1: does embb's commanded PRB ceiling actually bind the
live scheduler state, mechanistically confirmed -- not inferred?

E2 found embb demands 17.27 raw PRB at native load yet serves ~96% of
offered throughput at a 5-raw-PRB ceiling with zero loss/rejection. Two
candidate mechanisms: (i) embb's wildcard 0xFFFFFF SD structurally
bypasses ceiling enforcement in the scheduler; (ii) the ceiling DOES
bind, but embb's 1200B packets are simply far more spectrally efficient
than urllc's/mmtc's small packets, so 5 raw PRB genuinely carries ~96%
of 4Mbps without stressing the RLC AM buffer.

Static source reading (gNB_scheduler_dlsch.c) found no special-casing
of sd==0xffffff anywhere in the ceiling computation or per-slice
scheduling loop -- embb, at its configured position in the gNB conf's
snssaiList, gets internal sid=1 (mmtc=2, urllc=3), and the max_prbs
computation loop (`for i=1; i<dl_num_slice`) and the ceiling-reclamp
check apply identically regardless of sid or the underlying SD value.
That's not proof, though -- this script confirms it directly from the
LIVE scheduler state, using M41DBG instrumentation already built into
the current binary (gNB_scheduler_dlsch.c's own M41DBG ceiling/postpf
LOG_I lines, added for an earlier milestone, unmodified here): they
print, every ~10ms, each slice's sid, min_ratio/max_ratio, and the
ACTUAL computed dedi_prbs/min_prbs/max_prbs used by pf_dl_slice() that
slot.

Cold-start discipline: fresh stack, ceiling fixed to a low ratio (5%)
BEFORE any embb traffic exists, buffer confirmed drained, native embb
load (4000Kbps, the E2 scenario exactly), held long enough to gather a
large M41DBG sample. urllc and mmtc are left at their own native
traffic (unelevated, ceiling untouched -- default wide-open) purely as
a same-log sanity-check contrast: if the M41DBG-reading pipeline is
correct, their sid=2/sid=3 max_prbs should read near the full
n_rb_sched_init (uncapped), visibly different from embb's clamped
value, in the exact same log file at the exact same timestamps.

Never touches min_rbSize, tx_maxsize, or committed config/frozen
source -- reads existing instrumentation only, writes no new source.
New logic only in this script. Writes to experiments/results/m44e2b/
only.
"""
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m41_envelope_sweep as m41
import m44_scarcity_probe as m44a
import m44c_shed_sweep as m44c
import m44e_coldstart as m44e

RIG = m41.RIG
OUT_DIR = RIG / "experiments/results/m44e2b"
SLICE_ID = "embb"
CEILING_RATIO = 5  # matches E2's ceiling=5 (raw_prbs=5) exactly
HOLD_S = 120.0
SAMPLE_INTERVAL_S = 15.0

CEIL_RE = re.compile(
    r"M41DBG ceiling t=([\d.]+) frame=(\d+) slot=(\d+) sid=(\d+) min_ratio=(\d+) "
    r"max_ratio=(\d+) dedi_prbs=(-?\d+) min_prbs=(-?\d+) max_prbs=(-?\d+) "
    r"n_rb_sched_init=(\d+)"
)
POSTPF_RE = re.compile(
    r"M41DBG postpf t=([\d.]+) frame=(\d+) slot=(\d+) sid=(\d+) min_prbs=(-?\d+) "
    r"max_prbs=(-?\d+) remainUEs=(-?\d+) n_rb_sched=(\d+)"
)

SID_NAME = {1: "embb", 2: "mmtc", 3: "urllc"}  # per gNB conf's snssaiList order


def parse_m41dbg(gnb_log_path: Path, start_line: int) -> dict:
    if not gnb_log_path.exists():
        return {"ceiling_rows": [], "postpf_rows": [], "next_line": start_line}
    all_lines = gnb_log_path.read_text(errors="ignore").splitlines()
    new_lines = all_lines[start_line:]
    ceiling_rows, postpf_rows = [], []
    for line in new_lines:
        m = CEIL_RE.search(line)
        if m:
            ceiling_rows.append({
                "t": float(m.group(1)), "sid": int(m.group(4)),
                "min_ratio": int(m.group(5)), "max_ratio": int(m.group(6)),
                "dedi_prbs": int(m.group(7)), "min_prbs": int(m.group(8)),
                "max_prbs": int(m.group(9)), "n_rb_sched_init": int(m.group(10)),
            })
            continue
        m2 = POSTPF_RE.search(line)
        if m2:
            postpf_rows.append({
                "t": float(m2.group(1)), "sid": int(m2.group(4)),
                "min_prbs": int(m2.group(5)), "max_prbs": int(m2.group(6)),
                "remainUEs": int(m2.group(7)), "n_rb_sched": int(m2.group(8)),
            })
    return {"ceiling_rows": ceiling_rows, "postpf_rows": postpf_rows, "next_line": len(all_lines)}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    info = m44e.SLICE_INFO[SLICE_ID]
    bitrate = info["native_bitrate_kbps"] * 1.0  # native, exactly E2's scenario
    ts = time.strftime("%Y%m%d_%H%M%S")

    print(f"[m44e2b] === M44-E2b step 1: does embb's ceiling bind the live scheduler? "
          f"ceiling={CEILING_RATIO}% (~5 raw PRB), offered={bitrate}Kbps (native) ===",
          file=sys.stderr)

    if not m41.ensure_docker_core(force_fresh=True):
        print("[m44e2b] FATAL: docker core failed (phase 1)", file=sys.stderr)
        return 1
    if not m41.restart_native_stack(ts):
        m41.teardown(None, ts)
        return 1
    m41.start_traffic(1.0, ts)
    print("[m44e2b] gate-phase traffic launched, 30s pre-gate stabilization...", file=sys.stderr)
    time.sleep(30)
    gate_ok = m41.run_contention_gate(ts)
    print(f"[m44e2b] gate: {'PASS' if gate_ok else 'FAIL'}", file=sys.stderr)
    m41.teardown(None, ts)
    if not gate_ok:
        return 1

    if not m41.ensure_docker_core(force_fresh=True):
        return 1
    ts2 = time.strftime("%Y%m%d_%H%M%S")
    if not m41.restart_native_stack(ts2):
        m41.teardown(None, ts2)
        return 1

    # Ceiling fixed BEFORE any embb traffic exists -- cold-start discipline.
    m44c.set_ceiling(1, info["sd"], CEILING_RATIO, CEILING_RATIO)
    time.sleep(3)
    demand = m44a.poll_demand(polls=3, interval_s=1.0)
    buf_m = re.search(rf"sst1/sd{info['sd']}[^\n]*dl_mac_buffer_occupation=\s*([\d.]+)%", demand["stdout"])
    pre_buf_pct = float(buf_m.group(1)) if buf_m else None
    print(f"[m44e2b] pre-traffic dl_mac_buffer_occupation for embb = {pre_buf_pct}%", file=sys.stderr)

    ue_ip, ns = m44a.get_ue_ip(SLICE_ID)
    m41.start_traffic(1.0, ts2)  # urllc/mmtc native (unelevated, untouched ceiling) as a same-log contrast
    time.sleep(2)
    m41.pkill_pattern(f"iperf3 -c 172.22.0.50 -p {info['port']}")
    time.sleep(2)
    m44a.recreate_iperf3_target()

    traffic_log = OUT_DIR / f"traffic_embb_{ts2}.log"
    traffic_proc = m44e.launch_traffic(SLICE_ID, bitrate, ue_ip, ns, traffic_log)
    if traffic_proc.poll() is not None:
        print("[m44e2b] FATAL: traffic client failed to start", file=sys.stderr)
        m41.teardown(None, ts2)
        return 1

    gnb_log = RIG / f"experiments/logs/gnb_m41_{ts2}.log"
    all_ceiling_rows, all_postpf_rows = [], []
    gnb_line_cursor = len(gnb_log.read_text(errors="ignore").splitlines()) if gnb_log.exists() else 0
    t0 = time.time()
    try:
        n_samples = int(HOLD_S // SAMPLE_INTERVAL_S)
        for i in range(n_samples):
            time.sleep(SAMPLE_INTERVAL_S)
            elapsed = time.time() - t0

            m41dbg = parse_m41dbg(gnb_log, gnb_line_cursor)
            gnb_line_cursor = m41dbg["next_line"]
            all_ceiling_rows.extend(m41dbg["ceiling_rows"])
            all_postpf_rows.extend(m41dbg["postpf_rows"])

            thr = m44c.parse_recent_intervals(traffic_log, SAMPLE_INTERVAL_S)
            demand_now = m44a.poll_demand(polls=3, interval_s=1.0)
            buf_m2 = re.search(rf"sst1/sd{info['sd']}[^\n]*dl_mac_buffer_occupation=\s*([\d.]+)%",
                                demand_now["stdout"])
            buf_occ_pct = float(buf_m2.group(1)) if buf_m2 else None

            embb_ceiling_this_window = [r for r in m41dbg["ceiling_rows"] if r["sid"] == 1]
            embb_max_prbs = ([r["max_prbs"] for r in embb_ceiling_this_window]
                              if embb_ceiling_this_window else [])
            mmtc_ceiling_this_window = [r for r in m41dbg["ceiling_rows"] if r["sid"] == 2]
            urllc_ceiling_this_window = [r for r in m41dbg["ceiling_rows"] if r["sid"] == 3]

            print(f"[m44e2b] [t={elapsed:.0f}s] served={thr['mean_kbps']}Kbps buf_occ%={buf_occ_pct} "
                  f"M41DBG samples this window: embb(sid=1) n={len(embb_ceiling_this_window)} "
                  f"max_prbs={embb_max_prbs[:3]}{'...' if len(embb_max_prbs) > 3 else ''} | "
                  f"mmtc(sid=2) n={len(mmtc_ceiling_this_window)} | "
                  f"urllc(sid=3) n={len(urllc_ceiling_this_window)}",
                  file=sys.stderr)

            row = {"elapsed_s": round(elapsed, 1), "served_kbps": thr["mean_kbps"],
                   "dl_mac_buffer_occupation_pct": buf_occ_pct,
                   "n_ceiling_rows_this_window": len(m41dbg["ceiling_rows"]),
                   "n_postpf_rows_this_window": len(m41dbg["postpf_rows"])}
            (OUT_DIR / "throughput_trajectory.jsonl").open("a").write(json.dumps(row) + "\n")
    finally:
        traffic_proc.terminate()
        m41.teardown(None, ts2)

    (OUT_DIR / "m41dbg_ceiling_rows.jsonl").write_text(
        "\n".join(json.dumps(r) for r in all_ceiling_rows) + "\n")
    (OUT_DIR / "m41dbg_postpf_rows.jsonl").write_text(
        "\n".join(json.dumps(r) for r in all_postpf_rows) + "\n")

    print(f"[m44e2b] === DONE: {len(all_ceiling_rows)} M41DBG ceiling rows, "
          f"{len(all_postpf_rows)} M41DBG postpf rows captured, "
          f"results in {OUT_DIR} ===", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
