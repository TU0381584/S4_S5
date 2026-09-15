#!/usr/bin/env python3
"""M49b-1-1: honest post-M41-fix served-capacity/demand anchors at M8/M27's
REAL composition -- 3UE (1 UE/slice, native per-slice rate) and 6UE (2
UEs/slice), all three slices simultaneously, mmtc using its real bursty
(2s-on/6s-off) profile -- NOT M44's single-slice elevated-multiplier ramps.

Reuses this project's own established live-rig machinery unmodified:
m41_envelope_sweep (docker/gate/teardown/UE_DEF), m44_scarcity_probe
(SLICE_TRAFFIC/get_ue_ip/demand poll), m44c_shed_sweep (set_ceiling,
continuous-traffic launch+parse, RLC AM parse), m44e2b_ceiling_bind_check
(M41DBG scheduler-state parse). New in this file: bring-up for a genuine
2nd UE per slice (the subscriber profiles for this -- nrUE_slice4/5/6.conf,
mapped to embb/mmtc/urllc respectively via their own nssai_sd, confirmed
by direct inspection -- already exist in ORANSlice's own CONF dir but were
never wired into a reusable bring-up path before this milestone) and a
cursor-based bursty-aware throughput aggregator for mmtc (a continuous
-t3600 iperf3 session's own embedded interval timestamps are monotonic and
safe for m44c.parse_recent_intervals's trailing-window filter; mmtc's real
bursty profile instead loops short-lived iperf3 invocations, each
restarting its own internal clock at 0, which breaks that filter -- this
file's own parser tracks a file-line cursor per sample tick instead and
computes byte-weighted mean throughput over the wall-clock sample
interval directly, so genuine idle (off) time correctly contributes 0,
not a stale on-burst reading).

Never touches min_rbSize, tx_maxsize, action space, or committed
config/frozen source. New logic only. Writes to
experiments/results/m49b_1/ only.
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m41_envelope_sweep as m41  # noqa: E402
import m44_scarcity_probe as m44a  # noqa: E402
import m44c_shed_sweep as m44c  # noqa: E402
import m44e2b_ceiling_bind_check as m44e2b  # noqa: E402

RIG = m41.RIG
OUT_DIR = RIG / "experiments/results/m49b_1"

# Native (1x) per-slice bitrates, matching experiments/configs/
# traffic_profiles.yaml exactly (this project's own single source of
# truth for "what real traffic looks like" per slice), not M44's own
# elevated-multiplier values.
NATIVE_KBPS = {"embb": 4000.0, "urllc": 300.0, "mmtc": 50.0}
PACKET_LEN = {"embb": 1200, "urllc": 100, "mmtc": 80}
PORT = {"embb": 5201, "urllc": 5202, "mmtc": 5203}
# A standard iperf3 server instance handles one client at a time and
# rejects a second with "server is busy running a test" -- found live
# during this milestone's own smoke test (2 UEs on the same slice both
# targeting the primary port). Second UEs get their own dedicated port,
# same target container, requiring a 6-port server recreate below instead
# of m44_scarcity_probe.recreate_iperf3_target's own 3-port one (kept
# unmodified -- every other script still calls the 3-port version).
PORT2 = {"embb": 5204, "urllc": 5205, "mmtc": 5206}
SD = {"embb": 16777215, "urllc": 1, "mmtc": 2}  # matches saclb_live.yaml


def recreate_iperf3_target_6port() -> None:
    m41.sh("sudo docker rm -f iperf3-target >/dev/null 2>&1 || true")
    m41.sh(
        "sudo docker run -d --name iperf3-target --network demo-open5gs-public-net "
        "--ip 172.22.0.50 --restart unless-stopped --entrypoint sh networkstatic/iperf3 "
        "-c 'iperf3 -s -p 5201 & iperf3 -s -p 5202 & iperf3 -s -p 5203 & "
        "iperf3 -s -p 5204 & iperf3 -s -p 5205 & iperf3 -s -p 5206 & wait' >/dev/null"
    )
    time.sleep(3)

# Second-UE definitions for the 6UE condition. Confirmed by direct
# inspection (imsi + nssai_sd fields) that nrUE_slice4/5/6.conf carry the
# same slice identity as slice1/2/3 respectively, under a distinct
# subscriber (IMSI) -- these three conf files existed already but were
# never wired into a bring-up script before this milestone.
UE2_DEF = {
    "embb":  ("ue4", "nrUE_slice4.conf", "ue4ns", "veth-ue4h", "veth-ue4n", "10.99.4.1/30", "10.99.4.2/30"),
    "mmtc":  ("ue5", "nrUE_slice5.conf", "ue5ns", "veth-ue5h", "veth-ue5n", "10.99.5.1/30", "10.99.5.2/30"),
    "urllc": ("ue6", "nrUE_slice6.conf", "ue6ns", "veth-ue6h", "veth-ue6n", "10.99.6.1/30", "10.99.6.2/30"),
}


def bring_up_second_ue(slice_id: str, ts: str) -> tuple[bool, str]:
    """Mirrors m41.restart_native_stack's own ue2ns/ue3ns netns-creation
    and UE-launch pattern exactly, for a NEW netns/UE not already handled
    by that function. Idempotent netns creation, same as the original."""
    name, conf, ns, veth_h, veth_n, subnet_h, subnet_n = UE2_DEF[slice_id]
    exists = m41.sh(f"ip netns list | grep -q {ns}").returncode == 0
    if not exists:
        m41.sh(f"sudo ip netns add {ns}")
        m41.sh(f"sudo ip link add {veth_h} type veth peer name {veth_n}")
        m41.sh(f"sudo ip link set {veth_n} netns {ns}")
        m41.sh(f"sudo ip addr add {subnet_h} dev {veth_h}")
        m41.sh(f"sudo ip link set {veth_h} up")
        m41.sh(f"sudo ip netns exec {ns} ip addr add {subnet_n} dev {veth_n}")
        m41.sh(f"sudo ip netns exec {ns} ip link set {veth_n} up")
        m41.sh(f"sudo ip netns exec {ns} ip link set lo up")

    serveraddr = subnet_h.split("/")[0]
    cmd = (f"sudo ip netns exec {ns} {m41.BUILD_DIR}/nr-uesoftmodem -r 106 --numerology 1 --band 78 "
           f"-C 3619200000 --sa -O {m41.CONF_DIR}/{conf} --rfsim --rfsimulator.serveraddr {serveraddr}")
    ue_log = RIG / f"experiments/logs/{name}_m49b1_{ts}.log"
    m41.sh(f'tmux new-session -d -s {name} -c "{m41.BUILD_DIR}"')
    m41.sh(f'tmux send-keys -t {name} "{cmd} 2>&1 | tee {ue_log}" Enter')
    time.sleep(20)
    if "successfully configured" not in m41.sh(f"cat {ue_log}").stdout:
        return False, ""
    ip = m41.get_ue_ip(ns)
    return True, ip


def teardown_second_ues(slices: set[str]) -> None:
    for slice_id in slices:
        name, *_ = UE2_DEF[slice_id]
        m41.sh(f'tmux kill-session -t {name} 2>/dev/null || true')


def launch_bursty_mmtc(ue_ip: str, ns: str, log_path: Path, port: int = None) -> subprocess.Popen:
    """Real mmtc profile: 2s-on/6s-off loop, matching traffic_profiles.yaml
    exactly (not M44-E1/E1b's own continuous-elevated substitute)."""
    port = port or PORT["mmtc"]
    cmd = (f"bash -c \"while true; do "
           f"sudo ip netns exec {ns} stdbuf -oL -eL iperf3 -c {m44a.TARGET_CONTAINER_IP} "
           f"-p {port} -B {ue_ip} -u -b {NATIVE_KBPS['mmtc']}K -l {PACKET_LEN['mmtc']} "
           f"--reverse -i 1 -t 2 >> {log_path} 2>&1; sleep 6; done\"")
    fh = open(RIG / "experiments/logs" / f"{log_path.stem}_wrapper.log", "w")
    proc = subprocess.Popen(cmd, shell=True, stdout=fh, stderr=subprocess.STDOUT, start_new_session=True)
    time.sleep(2)
    return proc


def parse_bursty_window(log_path: Path, cursor_line: int, window_s: float) -> dict:
    """Cursor-based: only lines appended since cursor_line are considered,
    avoiding iperf3's per-invocation timestamp reset (each 2s burst is a
    fresh process, so embedded start/end times are NOT monotonic across
    the whole log the way a single continuous -t3600 session's are).
    Byte-weighted mean over the wall-clock window_s, so idle (off) time
    correctly contributes 0 rather than being silently skipped.

    Bug found and fixed after the first full_6ue run (re-derived offline
    from the already-collected raw logs, no new live time needed): each
    2s burst prints 2 genuine 1.00s-wide interval lines AND 2 summary
    lines (sender+receiver, both tagged, spanning the whole ~2.0-2.1s
    burst) that match the identical INTERVAL_RE shape -- naively treating
    every matched line as "1.0s of rate" double-(nearly triple-)counted
    the burst's own volume. Fixed by using each line's OWN reported
    (end_s - start_s) duration as its weight and excluding non-1s-wide
    lines from the per-second contribution -- summary lines are excluded
    entirely (they represent the same bytes the per-second lines already
    counted, not new volume), not reweighted, since including them at
    their own duration would still double-count the same underlying data."""
    if not log_path.exists():
        return {"mean_kbps": None, "n_new_lines": 0, "next_line": cursor_line}
    lines = log_path.read_text(errors="ignore").splitlines()
    new_lines = lines[cursor_line:]
    total_kbit_seconds = 0.0
    n_matched = 0
    for line in new_lines:
        m = m44c.INTERVAL_RE.search(line)
        if not m:
            continue
        start_s, end_s = float(m.group(1)), float(m.group(2))
        duration = end_s - start_s
        if not (0.5 <= duration <= 1.5):
            continue  # excludes the sender/receiver summary lines (span ~2s), not just reweights them
        rate_kbps = float(m.group(3)) * m44c.UNIT_TO_KBPS[m.group(4)]
        total_kbit_seconds += rate_kbps * duration
        n_matched += 1
    mean_kbps = total_kbit_seconds / window_s if window_s > 0 else None
    return {"mean_kbps": mean_kbps, "n_new_lines": n_matched, "next_line": len(lines)}


def check_headroom() -> dict:
    ram = m41.sh("free -m | awk '/^Mem:/{print $7}'").stdout.strip()
    load = m41.sh("cat /proc/loadavg").stdout.strip()
    return {"ram_avail_mb": ram, "loadavg": load}


def run_condition(ue_count: int, hold_s: float, sample_interval_s: float, label: str) -> dict:
    ts = time.strftime("%Y%m%d_%H%M%S")
    print(f"[m49b1] === {label}: {ue_count}UE, native composition, COLD START "
          f"(embb=4000K urllc=300K mmtc=50K-bursty x {ue_count // 3} UE/slice) ===", file=sys.stderr)

    if not m41.ensure_docker_core(force_fresh=True):
        return {"label": label, "error": "docker_core_failed_phase1"}
    if not m41.restart_native_stack(ts):
        m41.teardown(None, ts)
        return {"label": label, "error": "bringup_failed_gate_phase"}
    m41.start_traffic(1.0, ts)
    print("[m49b1] gate-phase traffic launched, 30s pre-gate stabilization...", file=sys.stderr)
    time.sleep(30)
    gate_ok = m41.run_contention_gate(ts)
    print(f"[m49b1] gate: {'PASS' if gate_ok else 'FAIL'}", file=sys.stderr)
    m41.teardown(None, ts)
    if not gate_ok:
        return {"label": label, "error": "gate_failed"}

    if not m41.ensure_docker_core(force_fresh=True):
        return {"label": label, "error": "docker_core_failed_phase2"}
    ts2 = time.strftime("%Y%m%d_%H%M%S")
    if not m41.restart_native_stack(ts2):
        m41.teardown(None, ts2)
        return {"label": label, "error": "bringup_failed_phase2"}

    second_ues_up = set()
    ue2_ips = {}
    if ue_count == 6:
        for slice_id in ("embb", "mmtc", "urllc"):
            ok, ip = bring_up_second_ue(slice_id, ts2)
            if not ok:
                print(f"[m49b1] FATAL: second UE for {slice_id} did not attach", file=sys.stderr)
                teardown_second_ues(second_ues_up)
                m41.teardown(None, ts2)
                return {"label": label, "error": f"second_ue_bringup_failed_{slice_id}"}
            second_ues_up.add(slice_id)
            ue2_ips[slice_id] = ip
            print(f"[m49b1] second UE ({slice_id}) attached, ip={ip}", file=sys.stderr)

    headroom_pre = check_headroom()
    print(f"[m49b1] headroom before traffic: {headroom_pre}", file=sys.stderr)

    demand = m44a.poll_demand(polls=3, interval_s=1.0)
    pre_buf = {}
    for slice_id in ("embb", "urllc", "mmtc"):
        bm = re.search(rf"sst1/sd{SD[slice_id]}[^\n]*dl_mac_buffer_occupation=\s*([\d.]+)%", demand["stdout"])
        pre_buf[slice_id] = float(bm.group(1)) if bm else None
    print(f"[m49b1] pre-traffic buffer occupation: {pre_buf}", file=sys.stderr)

    # ceilings wide open -- measuring the environment, not a policy
    for slice_id in ("embb", "urllc", "mmtc"):
        m44c.set_ceiling(1, SD[slice_id], 0, 100)
    time.sleep(2)

    embb_ip, embb_ns = m44a.get_ue_ip("embb")
    urllc_ip, urllc_ns = m44a.get_ue_ip("urllc")
    mmtc_ip, mmtc_ns = m44a.get_ue_ip("mmtc")
    if ue_count == 6:
        recreate_iperf3_target_6port()
    else:
        m44a.recreate_iperf3_target()

    logs = {
        "embb_1": OUT_DIR / f"traffic_embb1_{label}_{ts2}.log",
        "urllc_1": OUT_DIR / f"traffic_urllc1_{label}_{ts2}.log",
        "mmtc_1": OUT_DIR / f"traffic_mmtc1_{label}_{ts2}.log",
    }
    procs = {}
    # embb: m44a.SLICE_TRAFFIC has no "embb" entry (M44-E1's own noted gap),
    # so launch it directly here, same stdbuf-fixed pattern as m44c's.
    def launch_continuous(slice_id: str, ue_ip: str, ns: str | None, log_path: Path, port: int = None) -> subprocess.Popen:
        port = port or PORT[slice_id]
        prefix = f"sudo ip netns exec {ns} " if ns else "sudo "
        cmd = (f"{prefix}stdbuf -oL -eL iperf3 -c {m44a.TARGET_CONTAINER_IP} -p {port} -B {ue_ip} "
               f"-u -b {NATIVE_KBPS[slice_id]}K -l {PACKET_LEN[slice_id]} --reverse -i 1 -t 3600")
        fh = open(log_path, "w")
        return subprocess.Popen(cmd, shell=True, stdout=fh, stderr=subprocess.STDOUT)

    procs["embb_1"] = launch_continuous("embb", embb_ip, embb_ns, logs["embb_1"])
    procs["urllc_1"] = launch_continuous("urllc", urllc_ip, urllc_ns, logs["urllc_1"])
    mmtc_procs = [launch_bursty_mmtc(mmtc_ip, mmtc_ns or "", logs["mmtc_1"])]

    if ue_count == 6:
        logs["embb_2"] = OUT_DIR / f"traffic_embb2_{label}_{ts2}.log"
        logs["urllc_2"] = OUT_DIR / f"traffic_urllc2_{label}_{ts2}.log"
        logs["mmtc_2"] = OUT_DIR / f"traffic_mmtc2_{label}_{ts2}.log"
        procs["embb_2"] = launch_continuous("embb", ue2_ips["embb"], UE2_DEF["embb"][2], logs["embb_2"], PORT2["embb"])
        procs["urllc_2"] = launch_continuous("urllc", ue2_ips["urllc"], UE2_DEF["urllc"][2], logs["urllc_2"], PORT2["urllc"])
        mmtc_procs.append(launch_bursty_mmtc(ue2_ips["mmtc"], UE2_DEF["mmtc"][2], logs["mmtc_2"], PORT2["mmtc"]))

    for name, p in procs.items():
        if p is not None and p.poll() is not None:
            print(f"[m49b1] FATAL: traffic client {name} failed to start", file=sys.stderr)
            for pp in list(procs.values()) + mmtc_procs:
                if pp is not None:
                    pp.terminate()
            teardown_second_ues(second_ues_up)
            m41.teardown(None, ts2)
            return {"label": label, "error": "traffic_launch_failed"}

    gnb_log = RIG / f"experiments/logs/gnb_m41_{ts2}.log"
    time.sleep(5)
    gnb_line_cursor = len(gnb_log.read_text(errors="ignore").splitlines())
    mmtc_cursors = {k: 0 for k in logs if k.startswith("mmtc")}

    samples = []
    t0 = time.time()
    n_samples = int(hold_s // sample_interval_s)
    try:
        for i in range(n_samples):
            time.sleep(sample_interval_s)
            elapsed = time.time() - t0
            headroom = check_headroom()
            try:
                if float(headroom["ram_avail_mb"]) < 300:
                    print(f"[m49b1] ABORT: RAM headroom critical ({headroom}), stopping cleanly", file=sys.stderr)
                    break
            except (ValueError, TypeError):
                pass

            embb1 = m44c.parse_recent_intervals(logs["embb_1"], sample_interval_s)
            urllc1 = m44c.parse_recent_intervals(logs["urllc_1"], sample_interval_s)
            mmtc1 = parse_bursty_window(logs["mmtc_1"], mmtc_cursors["mmtc_1"], sample_interval_s)
            mmtc_cursors["mmtc_1"] = mmtc1["next_line"]

            m41dbg = m44e2b.parse_m41dbg(gnb_log, gnb_line_cursor)
            gnb_line_cursor = len(gnb_log.read_text(errors="ignore").splitlines())

            def _mean(sid):
                xs = [r["max_prbs"] for r in m41dbg["ceiling_rows"] if r["sid"] == sid]
                return sum(xs) / len(xs) if xs else None

            row = {
                "sample_idx": i, "elapsed_s": round(elapsed, 1), "headroom": headroom,
                "embb1_served_kbps": embb1["mean_kbps"], "embb1_loss_pct": embb1["mean_loss_pct"],
                "urllc1_served_kbps": urllc1["mean_kbps"], "urllc1_loss_pct": urllc1["mean_loss_pct"],
                "mmtc1_served_kbps": mmtc1["mean_kbps"],
                "embb_m41dbg_maxprbs_mean": _mean(1),
                "urllc_m41dbg_maxprbs_mean": _mean(3),
                "mmtc_m41dbg_maxprbs_mean": _mean(2),
            }
            if ue_count == 6:
                embb2 = m44c.parse_recent_intervals(logs["embb_2"], sample_interval_s)
                urllc2 = m44c.parse_recent_intervals(logs["urllc_2"], sample_interval_s)
                mmtc2 = parse_bursty_window(logs["mmtc_2"], mmtc_cursors.get("mmtc_2", 0), sample_interval_s)
                mmtc_cursors["mmtc_2"] = mmtc2["next_line"]
                row.update({
                    "embb2_served_kbps": embb2["mean_kbps"], "embb2_loss_pct": embb2["mean_loss_pct"],
                    "urllc2_served_kbps": urllc2["mean_kbps"], "urllc2_loss_pct": urllc2["mean_loss_pct"],
                    "mmtc2_served_kbps": mmtc2["mean_kbps"],
                })
            samples.append(row)
            (OUT_DIR / f"trajectory_{label}.jsonl").open("a").write(json.dumps(row) + "\n")
            print(f"[m49b1] [{label} t={elapsed:.0f}s] embb1={row['embb1_served_kbps']}Kbps "
                  f"urllc1={row['urllc1_served_kbps']}Kbps mmtc1={row['mmtc1_served_kbps']}Kbps "
                  f"maxprbs(e/u/m)={row['embb_m41dbg_maxprbs_mean']}/{row['urllc_m41dbg_maxprbs_mean']}/"
                  f"{row['mmtc_m41dbg_maxprbs_mean']}", file=sys.stderr)
    finally:
        for p in list(procs.values()) + mmtc_procs:
            if p is not None:
                p.terminate()
        m41.pkill_pattern("while true.*iperf3")
        teardown_second_ues(second_ues_up)
        m41.teardown(None, ts2)

    return {"label": label, "ue_count": ue_count, "pre_traffic_buffer": pre_buf,
            "second_ue_ips": ue2_ips, "samples": samples, "ts2": ts2}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--condition", required=True,
                     choices=["mmtc_3ue", "mmtc_6ue", "urllc_3ue", "urllc_6ue", "embb_6ue", "smoke_6ue",
                              "full_3ue", "full_6ue"])
    ap.add_argument("--hold-s", type=float, default=150.0)
    ap.add_argument("--sample-interval-s", type=float, default=15.0)
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ue_count = 6 if "6ue" in args.condition else 3
    result = run_condition(ue_count, args.hold_s, args.sample_interval_s, args.condition)
    out_json = OUT_DIR / f"result_{args.condition}.json"
    out_json.write_text(json.dumps(result, indent=2))
    print(f"[m49b1] wrote {out_json}", file=sys.stderr)
    return 0 if "error" not in result else 1


if __name__ == "__main__":
    sys.exit(main())
