#!/usr/bin/env python3
"""M49b-3 -- falsify the pre-fix 3-vs-6-UE "complete collapse to
always-accept / OOD generalisation failure" claim, post-fix.

PRE-REGISTERED (given by the milestone spec, not decided here):
  prediction = the pre-fix 6UE "complete collapse" does NOT reproduce as
  a scarcity failure; any 3UE-vs-6UE block-pattern difference post-fix
  is trained-bias/noise, not OOD contention collapse.
  Escalate and report if 6UE SURPRISINGLY still collapses with the
  floor cleared.

One clean documented run (not a campaign -- the outcome is predicted,
per M49b-1-1 + M49b-2): the exact M8 seed-900 single-agent-DQN
checkpoint, 6UE (2 UEs/slice, M8's own native composition, NOT the
elevated E4 regime M49b-2 caught and discarded), post-fix
saclb_live.yaml, cold-start, ~5 episodes in one continuous session
(matching M8's own original multi-episode-per-session pattern).
Combines M49b-1-1's own 6UE bring-up (bring_up_second_ue, second-UE
netns/ports, real bursty mmtc) with M49b-2's own native-traffic
xapp-invocation pattern (run_native_m8_style) -- neither alone covers
"real 6UE bring-up feeding the actual policy checkpoint."
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m41_envelope_sweep as m41  # noqa: E402
import m44_scarcity_probe as m44a  # noqa: E402
import m46_mr3_live_revalidate as mr3  # noqa: E402
import m44e2b_ceiling_bind_check as m44e2b  # noqa: E402
import m42_floor_matrix as m42  # noqa: E402
import m49b1_native_colocation_probe as m49b1  # noqa: E402
import subprocess  # noqa: E402

RIG = mr3.RIG
OUT_DIR = RIG / "experiments/results/m49b_3"
OUT_DIR.mkdir(parents=True, exist_ok=True)

LIVE_CONFIG = RIG / "framework/qoe_oran_framework/configs/saclb_live.yaml"
CHECKPOINT = (RIG / "experiments/results/m8_live_anchor/offline_train/single_agent_dqn/"
              "seed900/train/dqn/offline_train/rep_0/checkpoint.pt")
EVAL_SEED = 3003  # new value, distinct from 3001 (discarded) and 3002 (M49b-2's 3UE run)
N_EPISODES = 5


def verify_config_clears_floor(cfg_path: Path) -> bool:
    text = cfg_path.read_text()
    ok = True
    for slice_id, nominal, floor, cap in m42.parse_slices(text):
        raw_prbs = m42.raw_prbs(floor)
        status = "OK" if raw_prbs >= 5 else "BELOW FLOOR"
        print(f"[m49b3] {slice_id}: floor={floor}% -> {raw_prbs} raw PRB [{status}]", file=sys.stderr)
        if raw_prbs < 5:
            ok = False
    return ok


def run_6ue_native_m8_style(eval_seed: int, episodes: int) -> dict:
    run_id = "m49b3_6ue_native_seed900"
    ts = time.strftime("%Y%m%d_%H%M%S")
    print(f"[m49b3] === {run_id} (eval_seed={eval_seed}, episodes={episodes}) === "
          f"COLD START, 6UE NATIVE composition (2 UEs/slice, NOT the E4-elevated regime)", file=sys.stderr)

    if not m41.ensure_docker_core(force_fresh=True):
        return {"error": "docker_core_failed_phase1"}
    if not m41.restart_native_stack(ts):
        m41.teardown(None, ts)
        return {"error": "bringup_failed_gate_phase"}
    m41.start_traffic(1.0, ts)
    print("[m49b3] gate-phase native traffic launched, 30s pre-gate stabilization...", file=sys.stderr)
    time.sleep(30)
    gate_ok = m41.run_contention_gate(ts)
    print(f"[m49b3] gate: {'PASS' if gate_ok else 'FAIL'}", file=sys.stderr)
    m41.teardown(None, ts)
    if not gate_ok:
        return {"error": "gate_failed"}

    if not m41.ensure_docker_core(force_fresh=True):
        return {"error": "docker_core_failed_phase2"}
    ts2 = time.strftime("%Y%m%d_%H%M%S")
    if not m41.restart_native_stack(ts2):
        m41.teardown(None, ts2)
        return {"error": "bringup_failed_phase2"}

    second_ues_up = set()
    ue2_ips = {}
    for slice_id in ("embb", "mmtc", "urllc"):
        ok, ip = m49b1.bring_up_second_ue(slice_id, ts2)
        if not ok:
            print(f"[m49b3] FATAL: second UE for {slice_id} did not attach", file=sys.stderr)
            m49b1.teardown_second_ues(second_ues_up)
            m41.teardown(None, ts2)
            return {"error": f"second_ue_bringup_failed_{slice_id}"}
        second_ues_up.add(slice_id)
        ue2_ips[slice_id] = ip
        print(f"[m49b3] second UE ({slice_id}) attached, ip={ip}", file=sys.stderr)

    # Native traffic for the PRIMARY (UE1/2/3) trio, reusing m41's own
    # established native launcher (embb/urllc continuous, mmtc real bursty).
    m41.start_traffic(1.0, ts2)
    time.sleep(2)

    # Native traffic for the SECOND UE of each slice, dedicated ports
    # (m49b1's own fix for the "server busy" collision found in M49b-1-1's
    # smoke test), same recreate-with-6-ports step.
    m49b1.recreate_iperf3_target_6port()
    logs2 = {
        "embb": OUT_DIR / f"traffic_embb2_{ts2}.log",
        "urllc": OUT_DIR / f"traffic_urllc2_{ts2}.log",
        "mmtc": OUT_DIR / f"traffic_mmtc2_{ts2}.log",
    }
    def launch_continuous2(slice_id: str, ue_ip: str, ns: str, log_path: Path, port: int) -> subprocess.Popen:
        cmd = (f"sudo ip netns exec {ns} stdbuf -oL -eL iperf3 -c {m44a.TARGET_CONTAINER_IP} -p {port} "
               f"-B {ue_ip} -u -b {m49b1.NATIVE_KBPS[slice_id]}K -l {m49b1.PACKET_LEN[slice_id]} "
               f"--reverse -i 1 -t 3600")
        fh = open(log_path, "w")
        return subprocess.Popen(cmd, shell=True, stdout=fh, stderr=subprocess.STDOUT)

    proc_embb2 = launch_continuous2("embb", ue2_ips["embb"], m49b1.UE2_DEF["embb"][2],
                                     logs2["embb"], m49b1.PORT2["embb"])
    proc_urllc2 = launch_continuous2("urllc", ue2_ips["urllc"], m49b1.UE2_DEF["urllc"][2],
                                      logs2["urllc"], m49b1.PORT2["urllc"])
    proc_mmtc2 = m49b1.launch_bursty_mmtc(ue2_ips["mmtc"], m49b1.UE2_DEF["mmtc"][2],
                                           logs2["mmtc"], m49b1.PORT2["mmtc"])
    for name, p in [("embb2", proc_embb2), ("urllc2", proc_urllc2), ("mmtc2", proc_mmtc2)]:
        if p.poll() is not None:
            print(f"[m49b3] FATAL: second-UE traffic client {name} failed to start", file=sys.stderr)
            for pp in (proc_embb2, proc_urllc2, proc_mmtc2):
                pp.terminate()
            m49b1.teardown_second_ues(second_ues_up)
            m41.teardown(None, ts2)
            return {"error": "second_ue_traffic_launch_failed"}
    time.sleep(3)

    gnb_log = RIG / f"experiments/logs/gnb_m41_{ts2}.log"
    omega_path = OUT_DIR / "seed900" / "omega_log.jsonl"
    omega_path.parent.mkdir(parents=True, exist_ok=True)
    xapp_console_log = OUT_DIR / f"xapp_console_{ts2}.log"

    xapp_cmd = [
        str(RIG / "venv/bin/python3"), str(mr3.XAPP_SCRIPT),
        "--config", str(LIVE_CONFIG), "--algorithm", "dqn",
        "--checkpoint", str(CHECKPOINT),
        "--gnb-id", "gnb-0", "--episodes", str(episodes), "--seed", str(eval_seed),
        "--run-id", run_id, "--omega-jsonl", str(omega_path),
        "--reward-mode", "sla",
    ]
    print(f"[m49b3] launching live policy loop: {' '.join(xapp_cmd)}", file=sys.stderr)
    t0 = time.time()
    xapp_timeout = mr3.XAPP_TIMEOUT_S * episodes  # scale timeout for multi-episode
    with open(xapp_console_log, "w") as fh:
        try:
            result = subprocess.run(xapp_cmd, cwd=str(mr3.FRAMEWORK_DIR), stdout=fh,
                                     stderr=subprocess.STDOUT, timeout=xapp_timeout)
            xapp_ok = (result.returncode == 0)
        except subprocess.TimeoutExpired:
            xapp_ok = False
            print("[m49b3] FATAL: saclb_xapp.py timed out", file=sys.stderr)
    elapsed = time.time() - t0
    print(f"[m49b3] xapp finished in {elapsed:.1f}s, ok={xapp_ok}", file=sys.stderr)

    proc_embb2.terminate()
    proc_urllc2.terminate()
    proc_mmtc2.terminate()
    m41.pkill_pattern("while true.*iperf3")
    m49b1.teardown_second_ues(second_ues_up)
    m41.teardown(None, ts2)

    if not xapp_ok:
        return {"error": "xapp_run_failed", "console_log": str(xapp_console_log)}
    return {"error": None, "ts2": ts2, "omega_path": omega_path, "elapsed_s": elapsed}


def main() -> int:
    assert CHECKPOINT.exists(), f"missing checkpoint: {CHECKPOINT}"
    print(f"[m49b3] verifying {LIVE_CONFIG} clears the 5-PRB scheduler floor before any live run...",
          file=sys.stderr)
    if not verify_config_clears_floor(LIVE_CONFIG):
        print("[m49b3] ABORT: config does not clear the floor, per standing constraint", file=sys.stderr)
        return 1
    print("[m49b3] config verified clear. Proceeding with the live run.", file=sys.stderr)

    result = run_6ue_native_m8_style(EVAL_SEED, N_EPISODES)
    print(f"[m49b3] run result: error={result.get('error')} elapsed_s={result.get('elapsed_s')}",
          file=sys.stderr)
    if result.get("error") is not None:
        return 1

    ts2 = result["ts2"]
    gnb_log = RIG / f"experiments/logs/gnb_m41_{ts2}.log"
    m41dbg = m44e2b.parse_m41dbg(gnb_log, 0)
    sid_name = {1: "embb", 2: "mmtc", 3: "urllc"}
    for sid, name in sid_name.items():
        vals = [r["max_prbs"] for r in m41dbg["ceiling_rows"] if r["sid"] == sid]
        if not vals:
            print(f"[m49b3] {name}: no M41DBG ceiling rows found", file=sys.stderr)
            continue
        below_floor_n = sum(1 for v in vals if v < 5)
        print(f"[m49b3] {name}: n_samples={len(vals)} mean_max_prbs={sum(vals)/len(vals):.2f} "
              f"below_floor_n={below_floor_n} (0 expected post-fix)", file=sys.stderr)

    print(f"[m49b3] omega log: {result['omega_path']}", file=sys.stderr)
    print(f"[m49b3] raw gNB log: {gnb_log}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
