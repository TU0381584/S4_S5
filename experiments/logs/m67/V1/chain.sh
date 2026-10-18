#!/bin/bash
D=/home/kmanojp/oranslice_rig/experiments/logs/m67/V1; cd $D
echo "$(date +%H:%M:%S) start" >> progress.log
tr '\n' '\0' < jobs.txt | xargs -0 -P 6 -I{} ./run_cmd.sh "{}"
echo "$(date +%H:%M:%S) ALL DONE" >> progress.log
