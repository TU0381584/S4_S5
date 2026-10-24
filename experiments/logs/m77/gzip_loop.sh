#!/bin/bash
# Compress every finished M73 log (idle >5 min); readers (m66_verify.read/find_eval) handle .gz.
cd /home/kmanojp/oranslice_rig/experiments/results
while true; do
  find m77 -name 'omega_log.jsonl' -mmin +5 -print0 2>/dev/null | xargs -0 -r -n 20 nice gzip -6
  grep -q 'ALL DONE' /home/kmanojp/oranslice_rig/experiments/logs/m77/progress.log 2>/dev/null && { sleep 400; find m77 -name 'omega_log.jsonl' -print0 | xargs -0 -r -n 20 gzip -6; exit 0; }
  sleep 180
done
