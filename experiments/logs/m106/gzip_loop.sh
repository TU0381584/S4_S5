#!/usr/bin/env bash
# Compress finished M106 training and validation logs. eval/ and eval_last/ stay plain while jobs run, because
# m67_run rereads eval_last/ at the end of each job; they are gzipped (lossless) after ALL DONE.
D=/home/kmanojp/oranslice_rig/experiments/results/m106
while ! grep -q 'ALL DONE' /home/kmanojp/oranslice_rig/experiments/logs/m106/done.txt 2>/dev/null; do
  [ -d $D ] && find $D \( -path '*/train/*' -o -path '*/val/*' \) -name 'omega_log.jsonl' -mmin +5 -exec gzip -9 {} \; 2>/dev/null
  sleep 120
done
find $D \( -path '*/train/*' -o -path '*/val/*' \) -name 'omega_log.jsonl' -exec gzip -9 {} \; 2>/dev/null
echo "gzip done $(date '+%H:%M:%S')" >> /home/kmanojp/oranslice_rig/experiments/logs/m106/done.txt
