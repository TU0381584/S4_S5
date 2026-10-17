#!/bin/bash
# Compress finished M66c logs (idle >10 min), except the disruption cells, whose merge step reads plain logs.
# Rule-selection logs are transient and deleted once idle, as in M66.
cd /home/kmanojp/oranslice_rig/experiments/results
while true; do
  find m66c_fresh -path 'm66c_fresh/C5_m4' -prune -o \( -path '*/eval/*' -o -path '*/train/*' \) -name 'omega_log.jsonl' -mmin +10 -print0 2>/dev/null | xargs -0 -r -n 4 nice gzip -6
  find m66c_fresh -path '*_select/*' -name 'omega_log.jsonl' -mmin +10 -delete 2>/dev/null
  grep -q 'ALL DONE' /home/kmanojp/oranslice_rig/experiments/logs/m66c/progress.log 2>/dev/null && exit 0
  sleep 300
done
