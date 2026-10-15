#!/bin/bash
cd /home/kmanojp/oranslice_rig/experiments/results
while true; do
  find m63_reviewer m63_scaling m63_scaling_mlp m63_m3 m63_m3_replication m63_fedprox -path '*/train/*' -name 'omega_log.jsonl' 2>/dev/null | while read -r t; do
    seeddir="${t%%/train/*}"; ev=$(find "$seeddir/eval" -name 'omega_log.jsonl' -mmin +3 2>/dev/null | head -1)
    [ -n "$ev" ] && gzip -6 "$t" && echo "$(date +%H:%M) gz $t" >> /home/kmanojp/oranslice_rig/experiments/logs/m63/full/gzip.log
  done
  grep -q 'ALL B DONE' /home/kmanojp/oranslice_rig/experiments/logs/m63/full/progress.log 2>/dev/null && exit 0
  sleep 300
done
