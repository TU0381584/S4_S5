#!/bin/bash
D=/home/kmanojp/oranslice_rig/experiments/logs/m75; cd $D
echo "$(date +%H:%M:%S) start" >> progress.log
tr '\n' '\0' < jobs.txt | xargs -0 -P 6 -I{} ./run_cmd.sh "{}"
echo "$(date +%H:%M:%S) STAGE1 DONE" >> progress.log
cd /home/kmanojp/oranslice_rig && venv/bin/python experiments/scripts/m75_select.py --jobs $D/jobs2.txt --out experiments/results/m75/C_selection.json > $D/select.out 2>&1
echo "$(date +%H:%M:%S) selection rc=$?" >> $D/progress.log
cd $D; [ -s jobs2.txt ] && tr '\n' '\0' < jobs2.txt | xargs -0 -P 6 -I{} ./run_cmd.sh "{}"
echo "$(date +%H:%M:%S) ALL DONE" >> progress.log
