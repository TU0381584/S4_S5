#!/bin/bash
cd /home/kmanojp/oranslice_rig
J=experiments/logs/m102
echo "launch $(date '+%F %T')" >> $J/done.txt
tr '\n' '\0' < $J/phase1.txt | xargs -0 -P5 -I{} $J/run_one.sh '{}'
echo "ALL DONE $(date '+%H:%M:%S')" >> $J/done.txt
