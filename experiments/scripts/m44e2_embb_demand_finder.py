#!/usr/bin/env python3
"""M44-E2 phase 1: find embb's realistic high-demand load via a wide-open
ceiling ramp, to scope the cold-start ceiling sweep.

embb's native profile (4Mbps/1200B sustained) is itself a high-throughput
flow -- unlike mmtc, driving embb somewhat above its native rate stays
recognizably eMBB-like (sustained high throughput IS eMBB's nature, not
a departure from it). M44-A never characterized embb's own demand curve
(it was excluded there since it "clears the floor natively"), so this is
the first real per-UE avg_prbs_dl measurement of embb across a load
ramp, using the exact same method M44-A used for urllc/mmtc
(m44_scarcity_probe.py's set_ceiling_wide_open/poll_demand, unmodified)
via a slice-agnostic ramped-traffic launcher (m44a's own
launch_ramped_traffic has no "embb" entry in its SLICE_TRAFFIC dict, so
this duplicates that ~10-line function reading from m44e_coldstart's
SLICE_INFO instead, which does have one).

Never touches min_rbSize, tx_maxsize, or committed config/frozen source.
New logic only. Writes to experiments/results/m44e2/ only.
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m41_envelope_sweep as m41
import m44_scarcity_probe as m44a
import m44e_coldstart as m44e

RIG = m41.RIG
OUT_DIR = RIG / "experiments/results/m44e2"
SLICE_ID = "embb"
MULTS = [1, 1.5, 2, 3, 4, 5, 6, 8, 10]

RNTI_RE = re.compile(r"rnti=(\d+): mean=([\d.]+) PRB\s+max=([\d.]+)")


def parse_rnti_means(stdout: str):
    return [(m.group(1), float(m.group(2)), float(m.group(3))) for m in RNTI_RE.finditer(stdout)]


def launch_ramped_traffic(slice_id: str, bitrate_kbps: float, ue_ip: str, ns: str | None) -> subprocess.Popen:
    info = m44e.SLICE_INFO[slice_id]
    prefix = f"sudo ip netns exec {ns} " if ns else "sudo "
    cmd = (f"{prefix}iperf3 -c {m44a.TARGET_CONTAINER_IP} -p {info['port']} -B {ue_ip} "
           f"-u -b {bitrate_kbps}K -l {info['packet_len']} --reverse -t 3600")
    log_path = OUT_DIR / f"traffic_{slice_id}_{bitrate_kbps}k.log"
    fh = open(log_path, "w")
    proc = subprocess.Popen(cmd, shell=True, stdout=fh, stderr=subprocess.STDOUT)
    time.sleep(2)
    return proc


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")

    print("[m44e2] === M44-E2 phase 1: embb demand-vs-load ramp at wide-open ceiling ===",
          file=sys.stderr)
    if not m41.ensure_docker_core(force_fresh=True):
        print("[m44e2] FATAL: docker core failed", file=sys.stderr)
        return 1
    if not m41.restart_native_stack(ts):
        m41.teardown(None, ts)
        return 1
    m41.start_traffic(1.0, ts)
    print("[m44e2] gate-phase traffic launched, 30s pre-gate stabilization...", file=sys.stderr)
    time.sleep(30)
    gate_ok = m41.run_contention_gate(ts)
    print(f"[m44e2] gate: {'PASS' if gate_ok else 'FAIL'}", file=sys.stderr)
    m41.teardown(None, ts)
    if not gate_ok:
        return 1

    if not m41.ensure_docker_core(force_fresh=True):
        return 1
    ts2 = time.strftime("%Y%m%d_%H%M%S")
    if not m41.restart_native_stack(ts2):
        m41.teardown(None, ts2)
        return 1
    m41.start_traffic(1.0, ts2)
    print("[m44e2] post-gate fresh stack up, 30s settle...", file=sys.stderr)
    time.sleep(30)

    info = m44e.SLICE_INFO[SLICE_ID]
    m44a.set_ceiling_wide_open(1, info["sd"])
    time.sleep(3)
    ue_ip, ns = m44a.get_ue_ip(SLICE_ID)

    results = []
    try:
        for mult in MULTS:
            m41.pkill_pattern(f"iperf3 -c 172.22.0.50 -p {info['port']}")
            time.sleep(2)
            m44a.recreate_iperf3_target()
            bitrate = info["native_bitrate_kbps"] * mult
            proc = launch_ramped_traffic(SLICE_ID, bitrate, ue_ip, ns)
            if proc.poll() is not None:
                print(f"[m44e2] WARNING: traffic failed to start at {mult}x, skipping", file=sys.stderr)
                continue
            time.sleep(10)
            demand = m44a.poll_demand(polls=15, interval_s=1.0)
            rntis = parse_rnti_means(demand["stdout"])
            target = max(rntis, key=lambda r: r[1]) if rntis else None
            row = {
                "mult": mult, "bitrate_kbps": bitrate, "rntis": rntis,
                "target_rnti": target[0] if target else None,
                "target_mean_prb": target[1] if target else None,
                "target_max_prb": target[2] if target else None,
            }
            results.append(row)
            (OUT_DIR / "demand_ramp_embb.jsonl").open("a").write(json.dumps(row) + "\n")
            print(f"[m44e2] mult={mult}x bitrate={bitrate}Kbps -> target rnti={row['target_rnti']} "
                  f"mean={row['target_mean_prb']} max={row['target_max_prb']} (all rntis: {rntis})",
                  file=sys.stderr)
            proc.terminate()
    finally:
        m41.teardown(None, ts2)

    print(f"[m44e2] === DONE, {len(results)} load levels tested, "
          f"results in {OUT_DIR / 'demand_ramp_embb.jsonl'} ===", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
