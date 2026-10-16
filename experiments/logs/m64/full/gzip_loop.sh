#!/bin/bash
cd /home/kmanojp/oranslice_rig/experiments/results
while true; do
  find m64 m65_reviewer m65_scaling m65_scaling_mlp m65_m3 m65_m3_replication m65_fedprox -path '*/train/*' -name 'omega_log.jsonl' 2>/dev/null | while read -r t; do
    seeddir="${t%%/train/*}"; ev=$(find "$seeddir/eval" -name 'omega_log.jsonl' -mmin +3 2>/dev/null | head -1)
    [ -n "$ev" ] && gzip -6 "$t" && echo "$(date +%H:%M) gz $t" >> /home/kmanojp/oranslice_rig/experiments/logs/m64/full/gzip.log
  done
  find m64 -path '*_select/*' -name 'omega_log.jsonl' -mmin +10 -delete 2>/dev/null
  grep -q 'ALL B DONE' /home/kmanojp/oranslice_rig/experiments/logs/m64/full/progress.log 2>/dev/null && exit 0
  sleep 300
done
