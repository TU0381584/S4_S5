#!/usr/bin/env bash
# M43-P1: launches traffic matching experiments/configs/traffic_profiles.yaml
# EXACTLY (bitrate/packet_len_bytes/mode per slice) -- the ORIGINAL Paper #4
# campaign's traffic spec, deliberately NOT m41_envelope_sweep.py's own
# start_traffic() (different bitrates), since P1 requires reproducing the
# submitted campaign's actual traffic, not M41's.
#
# No existing script in this repo launches iperf3 from this file (checked:
# zero references to its IPs anywhere in experiments/scripts/) -- the
# original campaign's traffic was evidently started by hand, matching this
# spec. New script, does not touch any existing file.
set -uo pipefail

TARGET_IP=172.22.0.50
LOG_DIR="$HOME/oranslice_rig/experiments/logs/m43"
mkdir -p "$LOG_DIR"

echo "[m43-traffic] embb: UDP 4M, 1200B, sustained, 192.168.100.2 -> $TARGET_IP:5201"
sudo iperf3 -c "$TARGET_IP" -p 5201 -B 192.168.100.2 -u -b 4M -l 1200 --reverse -t 3600 \
  > "$LOG_DIR/embb_traffic.log" 2>&1 &
echo $! > "$LOG_DIR/embb_traffic.pid"

echo "[m43-traffic] urllc: UDP 300K, 100B, sustained, 192.168.102.2 (ue3ns) -> $TARGET_IP:5202"
sudo ip netns exec ue3ns iperf3 -c "$TARGET_IP" -p 5202 -B 192.168.102.2 -u -b 300K -l 100 --reverse -t 3600 \
  > "$LOG_DIR/urllc_traffic.log" 2>&1 &
echo $! > "$LOG_DIR/urllc_traffic.pid"

echo "[m43-traffic] mmtc: UDP 50K, 80B, bursty 2s-on/6s-off, 192.168.200.2 (ue2ns) -> $TARGET_IP:5203"
(
  while true; do
    sudo ip netns exec ue2ns iperf3 -c "$TARGET_IP" -p 5203 -B 192.168.200.2 -u -b 50K -l 80 --reverse -t 2 \
      >> "$LOG_DIR/mmtc_traffic.log" 2>&1
    sleep 6
  done
) &
echo $! > "$LOG_DIR/mmtc_traffic.pid"

echo "[m43-traffic] all 3 slices launched, PIDs in $LOG_DIR/*.pid"
