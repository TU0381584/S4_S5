#!/usr/bin/env python3
"""M44-A: real per-slice PRB demand vs offered load, ceiling wide open.

For ONE target slice (urllc or mmtc), brings up the standard 3-UE stack,
passes the contention gate, forces the target slice's ceiling wide open
(min=0,max=100 -- so nothing artificially constrains what we're measuring),
then ramps that slice's OWN offered bitrate through a series of levels,
polling real avg_prbs_dl (via the existing probe_e2_preconditions.py P3
tool, unmodified) at each level. The other two slices keep running their
normal traffic_profiles.yaml-equivalent load throughout (needed for the
gate, which checks embb specifically, and to keep the measurement
realistic -- not an idle carrier).

Does not touch qoe_oran_framework/ or any committed config. Reuses
m41_envelope_sweep.py's bring-up/gate/teardown functions unmodified (import,
not edit). Writes to experiments/results/m44/ only.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m41_envelope_sweep as m41

RIG = m41.RIG
OUT_DIR = RIG / "experiments/results/m44"
TARGET_CONTAINER_IP = "172.22.0.50"

# native bitrate, port, packet size per traffic_profiles.yaml
SLICE_TRAFFIC = {
    "urllc": {"port": 5202, "packet_len": 100, "sd": 1, "native_bitrate_kbps": 300},
    "mmtc": {"port": 5203, "packet_len": 80, "sd": 2, "native_bitrate_kbps": 50},
}


def get_ue_ip(slice_id: str) -> tuple[str, str | None]:
    _, _, _, ns = m41.UE_DEF[slice_id]
    prefix = f"sudo ip netns exec {ns} " if ns else ""
    out = m41.sh(f"{prefix}ip -4 addr show oaitun_ue1").stdout
    import re
    mm = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", out)
    return (mm.group(1) if mm else ""), ns


def set_ceiling_wide_open(sst: int, sd: int) -> None:
    cmd = (f"cd {RIG}/framework && {RIG}/venv/bin/python3 -m "
           f"qoe_oran_framework.scripts.probe_e2_preconditions "
           f"--send-control --sst {sst} --sd {sd} --min-ratio 0 --max-ratio 100 "
           f"--polls 1 --interval-s 0.1")
    r = m41.sh(cmd, timeout=30)
    print(f"[m44] set ceiling wide open sst={sst} sd={sd}: rc={r.returncode}", file=sys.stderr)


def poll_demand(polls: int = 20, interval_s: float = 1.0) -> dict:
    cmd = (f"cd {RIG}/framework && {RIG}/venv/bin/python3 -m "
           f"qoe_oran_framework.scripts.probe_e2_preconditions "
           f"--polls {polls} --interval-s {interval_s}")
    r = m41.sh(cmd, timeout=int(polls * interval_s) + 60)
    return {"stdout": r.stdout, "stderr": r.stderr, "returncode": r.returncode}


def recreate_iperf3_target() -> None:
    # The known "server is busy running a test" port-wedge bug: a killed
    # client doesn't reliably release the SERVER's own internal busy state
    # in time for the next connection, even after a multi-second wait. The
    # established fix throughout this project (run_stage15_n128_campaign.sh's
    # own maybe_fix_iperf3(), M43's own launcher) is recreating the container
    # fresh, not waiting longer. Doing this between every load level, not
    # just on failure, since silent failure here previously went undetected
    # for 6 of 7 load levels in this exact script's own first run.
    m41.sh("sudo docker rm -f iperf3-target >/dev/null 2>&1 || true")
    m41.sh(
        "sudo docker run -d --name iperf3-target --network demo-open5gs-public-net "
        "--ip 172.22.0.50 --restart unless-stopped --entrypoint sh networkstatic/iperf3 "
        "-c 'iperf3 -s -p 5201 & iperf3 -s -p 5202 & iperf3 -s -p 5203 & wait' >/dev/null"
    )
    time.sleep(3)


def launch_ramped_traffic(slice_id: str, bitrate_kbps: float, ue_ip: str, ns: str | None) -> subprocess.Popen:
    info = SLICE_TRAFFIC[slice_id]
    prefix = f"sudo ip netns exec {ns} " if ns else "sudo "
    cmd = (f"{prefix}iperf3 -c {TARGET_CONTAINER_IP} -p {info['port']} -B {ue_ip} "
           f"-u -b {bitrate_kbps}K -l {info['packet_len']} --reverse -t 3600")
    log_path = OUT_DIR / f"traffic_{slice_id}_{bitrate_kbps}k.log"
    fh = open(log_path, "w")
    proc = subprocess.Popen(cmd, shell=True, stdout=fh, stderr=subprocess.STDOUT)
    # Verify the client actually connected (didn't immediately die on the
    # port-wedge error) before trusting this load level's measurement.
    time.sleep(2)
    if proc.poll() is not None:
        err_text = log_path.read_text(errors="ignore") if log_path.exists() else ""
        print(f"[m44] WARNING: traffic client exited immediately (rc={proc.returncode}): "
              f"{err_text[:200]!r}", file=sys.stderr)
    return proc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slice", required=True, choices=["urllc", "mmtc"])
    ap.add_argument("--load-multipliers", type=float, nargs="+",
                     default=[1, 2, 5, 10, 20, 50, 100])
    ap.add_argument("--settle-s", type=float, default=20.0)
    ap.add_argument("--polls-per-level", type=int, default=15)
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    slice_id = args.slice
    info = SLICE_TRAFFIC[slice_id]
    ts = time.strftime("%Y%m%d_%H%M%S")

    print(f"[m44] === M44-A demand probe: slice={slice_id} ===", file=sys.stderr)
    if not m41.ensure_docker_core(force_fresh=True):
        print("[m44] FATAL: docker core failed", file=sys.stderr)
        return 1
    if not m41.restart_native_stack(ts):
        print("[m44] FATAL: bring-up failed", file=sys.stderr)
        m41.teardown(None, ts)
        return 1
    m41.start_traffic(1.0, ts)  # normal native traffic on all 3 slices as baseline
    print("[m44] traffic launched, 30s pre-gate stabilization...", file=sys.stderr)
    time.sleep(30)

    gate_ok = m41.run_contention_gate(ts)
    print(f"[m44] gate: {'PASS' if gate_ok else 'FAIL'}", file=sys.stderr)
    if not gate_ok:
        print("[m44] GATE FAILED, aborting", file=sys.stderr)
        m41.teardown(None, ts)
        return 1

    # fresh restart post-gate, matching established M41 discipline
    m41.teardown(None, ts)
    if not m41.ensure_docker_core(force_fresh=True):
        return 1
    ts2 = time.strftime("%Y%m%d_%H%M%S")
    if not m41.restart_native_stack(ts2):
        m41.teardown(None, ts2)
        return 1
    m41.start_traffic(1.0, ts2)
    print("[m44] post-gate fresh stack up, 30s settle...", file=sys.stderr)
    time.sleep(30)

    # Force the target slice's ceiling wide open -- no policy running, direct write.
    set_ceiling_wide_open(1, info["sd"])
    time.sleep(3)

    ue_ip, ns = get_ue_ip(slice_id)
    print(f"[m44] {slice_id} UE IP: {ue_ip} (ns={ns})", file=sys.stderr)

    # Stop the native-rate traffic for this slice (started by start_traffic above)
    # so we control its exact bitrate ourselves for the ramp.
    m41.pkill_pattern(f"iperf3 -c 172.22.0.50 -p {info['port']}")
    time.sleep(2)

    results = []
    traffic_proc = None
    try:
        for mult in args.load_multipliers:
            bitrate = info["native_bitrate_kbps"] * mult
            print(f"[m44] --- {slice_id} @ {mult}x native ({bitrate} Kbps) ---", file=sys.stderr)
            if traffic_proc is not None:
                traffic_proc.terminate()
                time.sleep(1)
            recreate_iperf3_target()
            traffic_proc = launch_ramped_traffic(slice_id, bitrate, ue_ip, ns)
            if traffic_proc.poll() is not None:
                print(f"[m44] FATAL: traffic client for {mult}x failed to start "
                      f"(rc={traffic_proc.returncode}), aborting this slice's ramp", file=sys.stderr)
                break
            print(f"[m44] settling {args.settle_s}s...", file=sys.stderr)
            time.sleep(args.settle_s)
            if traffic_proc.poll() is not None:
                print(f"[m44] FATAL: traffic client for {mult}x died during settle "
                      f"(rc={traffic_proc.returncode}), aborting this slice's ramp", file=sys.stderr)
                break

            ram_mb = m41.ram_available_mb()
            demand = poll_demand(polls=args.polls_per_level, interval_s=1.0)
            print(demand["stdout"][-800:], file=sys.stderr)

            # check for RLC max-retx so far
            ue_log_names = {"urllc": "ue3", "mmtc": "ue2"}
            ue_log = RIG / f"experiments/logs/{ue_log_names[slice_id]}_m41_{ts2}.log"
            retx_count = 0
            if ue_log.exists():
                retx_count = ue_log.read_text(errors="ignore").count("max RETX reached")

            row = {
                "slice": slice_id, "load_mult": mult, "bitrate_kbps": bitrate,
                "ram_available_mb": ram_mb, "retx_count_cumulative": retx_count,
                "probe_stdout": demand["stdout"],
            }
            results.append(row)
            (OUT_DIR / f"demand_curve_{slice_id}.jsonl").open("a").write(json.dumps(row) + "\n")

            if retx_count > 0:
                print(f"[m44] WARNING: {retx_count} max-RETX events detected, stopping ramp", file=sys.stderr)
                break
            if ram_mb < 300:
                print(f"[m44] WARNING: RAM critically low ({ram_mb}MB), stopping ramp", file=sys.stderr)
                break
    finally:
        if traffic_proc is not None:
            traffic_proc.terminate()
        m41.teardown(None, ts2)

    print(f"[m44] === DONE, {len(results)} levels tested, results in "
          f"{OUT_DIR / f'demand_curve_{slice_id}.jsonl'} ===", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
