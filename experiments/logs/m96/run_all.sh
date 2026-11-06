#!/bin/bash
# phase 1 (training, rules, shifted-load evaluations), then phase 2 (transfer of the fresh 7-gNB checkpoints)
cd /home/kmanojp/oranslice_rig
J=experiments/logs/m96
tr '\n' '\0' < $J/phase1.txt | xargs -0 -P5 -I{} $J/run_one.sh '{}'
echo "phase1 complete $(date '+%H:%M:%S')" >> $J/done.txt
tr '\n' '\0' < $J/phase2.txt | xargs -0 -P4 -I{} $J/run_one.sh '{}'
echo "ALL DONE $(date '+%H:%M:%S')" >> $J/done.txt
