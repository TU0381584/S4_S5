#!/bin/bash
# M109 launcher. Safe to run again after an interruption: jobs already recorded as "exit 0" are skipped.
cd /home/kmanojp/oranslice_rig
J=experiments/logs/m109
echo "launch $(date '+%F %T')" >> $J/done.txt
tr '\n' '\0' < $J/jobs.txt | xargs -0 -P6 -I{} $J/run_one.sh '{}'
echo "ALL DONE $(date '+%F %T')" >> $J/done.txt
