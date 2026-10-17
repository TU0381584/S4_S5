#!/bin/bash
# Compress finished evaluation and training logs (idle >10 min); m66_verify.read handles .gz transparently.
cd /home/kmanojp/oranslice_rig/experiments/results
while true; do
  find m66b_fresh \( -path '*/eval/*' -o -path '*/train/*' \) -name 'omega_log.jsonl' -mmin +10 -print0 2>/dev/null | xargs -0 -r -n 4 nice gzip -6
  grep -q 'ALL DONE' /home/kmanojp/oranslice_rig/experiments/logs/m66b/progress.log 2>/dev/null && exit 0
  sleep 300
done
