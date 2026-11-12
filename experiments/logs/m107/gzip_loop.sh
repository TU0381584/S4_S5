#!/usr/bin/env bash
# Compress M107 logs (training and evaluation) 3 minutes after they were last written. Each job runs one seed and
# reads its evaluation log immediately after writing it, so a log older than 3 minutes is final. Every reader of
# m107 is gzip-aware (m66_verify.read and the scripts updated for M107).
D=/home/kmanojp/oranslice_rig/experiments/results/m107
while ! grep -q 'ALL DONE' /home/kmanojp/oranslice_rig/experiments/logs/m107/done.txt 2>/dev/null; do
  [ -d $D ] && find $D -name 'omega_log.jsonl' -mmin +3 -exec gzip -6 {} \; 2>/dev/null
  sleep 120
done
sleep 200; find $D -name 'omega_log.jsonl' -exec gzip -6 {} \; 2>/dev/null
echo "gzip done $(date '+%H:%M:%S')" >> /home/kmanojp/oranslice_rig/experiments/logs/m107/done.txt
