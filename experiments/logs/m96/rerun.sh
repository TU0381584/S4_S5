#!/bin/bash
# M96 rerun of the 20 jobs that failed at 14:50 on 2026-11-07 with "No space left on device" (16 shift evaluations, then the 4 transfers)
cd /home/kmanojp/oranslice_rig
J=experiments/logs/m96
mkdir -p $J/failed_nospace && for n in $(cut -d'|' -f1 $J/rerun1.txt $J/phase2.txt); do [ -f $J/$n.log ] && mv $J/$n.log $J/failed_nospace/; done
echo "RERUN start $(date '+%H:%M:%S')" >> $J/done.txt
tr '\n' '\0' < $J/rerun1.txt | xargs -0 -P5 -I{} $J/run_one.sh '{}'
echo "rerun phase1 complete $(date '+%H:%M:%S')" >> $J/done.txt
tr '\n' '\0' < $J/phase2.txt | xargs -0 -P4 -I{} $J/run_one.sh '{}'
echo "RERUN ALL DONE $(date '+%H:%M:%S')" >> $J/done.txt
