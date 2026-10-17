#!/bin/bash
cd /home/kmanojp/oranslice_rig/experiments/results
while true; do
  find m66_fresh m66_repro -path '*/train/*' -name 'omega_log.jsonl' 2>/dev/null | while read -r t; do
    seeddir="${t%%/train/*}"; ev=$(find "$seeddir/eval" -name 'omega_log.jsonl' -mmin +3 2>/dev/null | head -1)
    [ -n "$ev" ] && gzip -6 "$t"
  done
  find m66_fresh m66_repro -path '*_select/*' -name 'omega_log.jsonl' -mmin +10 -delete 2>/dev/null
  grep -q 'ALL DONE' /home/kmanojp/oranslice_rig/experiments/logs/m66/progress.log 2>/dev/null && exit 0
  sleep 300
done
