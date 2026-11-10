#!/usr/bin/env bash
# Compress finished M104 training and rule-tuning logs (never read again); evaluation logs are left plain.
D=/home/kmanojp/oranslice_rig/experiments/results/m104
while ! grep -q 'ALL DONE' /home/kmanojp/oranslice_rig/experiments/logs/m104/done.txt 2>/dev/null; do
  [ -d $D ] && find $D \( -path '*/train/*' -o -path '*_select/*' -o -path '*/val/*' \) -name 'omega_log.jsonl' -mmin +5 -exec gzip -9 {} \; 2>/dev/null
  sleep 120
done
find $D \( -path '*/train/*' -o -path '*_select/*' -o -path '*/val/*' \) -name 'omega_log.jsonl' -exec gzip -9 {} \; 2>/dev/null
echo "gzip done $(date '+%H:%M:%S')" >> /home/kmanojp/oranslice_rig/experiments/logs/m104/done.txt
