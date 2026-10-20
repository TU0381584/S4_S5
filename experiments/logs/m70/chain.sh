#!/bin/bash
D=/home/kmanojp/oranslice_rig/experiments/logs/m70; cd $D
echo "$(date +%H:%M:%S) start phase1" >> progress.log
tr '\n' '\0' < jobs_phase1.txt | xargs -0 -P 6 -I{} ./run_cmd.sh "{}"
echo "$(date +%H:%M:%S) phase1 done" >> progress.log
/home/kmanojp/oranslice_rig/venv/bin/python3 /home/kmanojp/oranslice_rig/experiments/scripts/m70_select_mappo.py >> progress.log 2>&1 || { echo "$(date +%H:%M:%S) SELECTION FAILED" >> progress.log; exit 1; }
tr '\n' '\0' < jobs_phase2.txt | xargs -0 -P 6 -I{} ./run_cmd.sh "{}"
echo "$(date +%H:%M:%S) ALL DONE" >> progress.log
