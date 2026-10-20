#!/bin/bash
# Compress finished M70 logs (idle >10 min), except the disruption cells, whose merge step reads plain logs.
# Rule-selection logs are transient and deleted once idle, as in M66.
cd /home/kmanojp/oranslice_rig/experiments/results
while true; do
  find m70 -path 'm70/C5_m4' -prune -o \( -path '*/eval/*' -o -path '*/train/*' \) -name 'omega_log.jsonl' -mmin +10 -print0 2>/dev/null | xargs -0 -r -n 4 nice gzip -6
  find m70 -path '*_select/*' -name 'omega_log.jsonl' -mmin +10 -delete 2>/dev/null
  grep -q 'ALL DONE' /home/kmanojp/oranslice_rig/experiments/logs/m70/progress.log 2>/dev/null && exit 0
  sleep 300
done
