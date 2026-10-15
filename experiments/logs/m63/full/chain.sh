#!/bin/bash
cd /home/kmanojp/oranslice_rig/experiments/logs/m63/full
echo "$(date +%H:%M:%S) start A" >> progress.log
tr '\n' '\0' < jobs_A.txt | xargs -0 -P 5 -I{} ./dispatch.sh "{}"
echo "$(date +%H:%M:%S) ALL A DONE" >> progress.log
sed 's/^/C:/' jobs_cmdB.txt | tr '\n' '\0' | xargs -0 -P 5 -I{} ./dispatch.sh "{}"
cd /home/kmanojp/oranslice_rig
for d in m63_m4 m63_m4_replication; do ./venv/bin/python3 experiments/scripts/m62_m4_merge.py experiments/results/$d >> experiments/logs/m63/full/progress.log 2>&1; done
echo "$(date +%H:%M:%S) ALL B DONE" >> experiments/logs/m63/full/progress.log
