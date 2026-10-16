#!/bin/bash
D=/home/kmanojp/oranslice_rig/experiments/logs/m64/full; cd $D
echo "$(date +%H:%M:%S) start A" >> progress.log
tr '\n' '\0' < jobs_A.txt | xargs -0 -P 5 -I{} ./dispatch.sh "{}"
echo "$(date +%H:%M:%S) ALL A DONE" >> progress.log
tr '\n' '\0' < jobs_B.txt | xargs -0 -P 5 -I{} ./dispatch.sh "{}"
cd /home/kmanojp/oranslice_rig
for d in m65_m4 m65_m4_replication; do ./venv/bin/python3 experiments/scripts/m62_m4_merge.py experiments/results/$d >> $D/progress.log 2>&1; done
echo "$(date +%H:%M:%S) ALL B DONE" >> $D/progress.log
