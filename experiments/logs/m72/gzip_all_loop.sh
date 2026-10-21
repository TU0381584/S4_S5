#!/bin/bash
# Compress every finished M72 log (idle >5 min), including rule-evaluation logs under offline_eval/ that the other loop skips.
cd /home/kmanojp/oranslice_rig/experiments/results
while true; do
  find m72 -name 'omega_log.jsonl' -mmin +5 -print0 2>/dev/null | xargs -0 -r -n 20 nice gzip -6
  grep -q 'ALL DONE' /home/kmanojp/oranslice_rig/experiments/logs/m72/progress.log 2>/dev/null && exit 0
  sleep 180
done
