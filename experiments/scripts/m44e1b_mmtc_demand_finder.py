#!/usr/bin/env python3
"""M44-E1b phase 1: find the mmtc offered load at which UNCAPPED demand
reaches ~9 raw PRB, matching the regime that produced urllc's graded
band in M44-D (~3600Kbps offered, ~9-10 PRB uncapped demand). E1 showed
mmtc clears its own 50x/2500Kbps floor-clearing load cleanly with no
shed band, so the band (if it exists) sits at a higher load.

Interpolating M44-A's own already-committed mmtc demand curve
(50x/2500Kbps -> 7.07 PRB mean, 100x/5000Kbps -> 18.53 PRB mean, both
from experiments/results/m44/demand_curve_mmtc.jsonl) with a log-log fit
puts the ~9 PRB crossing around ~59x -- this script ramps a fine grid of
multipliers around that estimate at a WIDE-OPEN ceiling and records the
real per-UE avg_prbs_dl demand at each level directly (same method M44-A
itself used, unmodified via m44_scarcity_probe.py's own
launch_ramped_traffic/poll_demand), rather than trusting the
interpolation.

Never touches min_rbSize, tx_maxsize, or committed config/frozen source.
New logic only. Writes to experiments/results/m44e1b/ only.
"""
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m41_envelope_sweep as m41
import m44_scarcity_probe as m44a

RIG = m41.RIG
OUT_DIR = RIG / "experiments/results/m44e1b"
SLICE_ID = "mmtc"
MULTS = [52, 55, 58, 60, 62, 65, 70, 75, 80]

RNTI_RE = re.compile(r"rnti=(\d+): mean=([\d.]+) PRB\s+max=([\d.]+)")


def parse_rnti_means(stdout: str):
    return [(m.group(1), float(m.group(2)), float(m.group(3))) for m in RNTI_RE.finditer(stdout)]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")

    print("[m44e1b] === M44-E1b phase 1: mmtc demand-vs-load ramp at wide-open ceiling ===",
          file=sys.stderr)
    if not m41.ensure_docker_core(force_fresh=True):
        print("[m44e1b] FATAL: docker core failed", file=sys.stderr)
        return 1
    if not m41.restart_native_stack(ts):
        m41.teardown(None, ts)
        return 1
    m41.start_traffic(1.0, ts)
    print("[m44e1b] gate-phase traffic launched, 30s pre-gate stabilization...", file=sys.stderr)
    time.sleep(30)
    gate_ok = m41.run_contention_gate(ts)
    print(f"[m44e1b] gate: {'PASS' if gate_ok else 'FAIL'}", file=sys.stderr)
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
    print("[m44e1b] post-gate fresh stack up, 30s settle...", file=sys.stderr)
    time.sleep(30)

    info = m44a.SLICE_TRAFFIC[SLICE_ID]
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
            proc = m44a.launch_ramped_traffic(SLICE_ID, bitrate, ue_ip, ns)
            if proc.poll() is not None:
                print(f"[m44e1b] WARNING: traffic failed to start at {mult}x, skipping", file=sys.stderr)
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
            (OUT_DIR / "demand_ramp_mmtc.jsonl").open("a").write(json.dumps(row) + "\n")
            print(f"[m44e1b] mult={mult}x bitrate={bitrate}Kbps -> target rnti={row['target_rnti']} "
                  f"mean={row['target_mean_prb']} max={row['target_max_prb']} (all rntis: {rntis})",
                  file=sys.stderr)
            proc.terminate()
    finally:
        m41.teardown(None, ts2)

    print(f"[m44e1b] === DONE, {len(results)} load levels tested, "
          f"results in {OUT_DIR / 'demand_ramp_mmtc.jsonl'} ===", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
