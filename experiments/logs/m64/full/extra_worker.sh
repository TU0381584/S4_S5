#!/bin/bash
D=/home/kmanojp/oranslice_rig/experiments/logs/m64/full; cd $D
until [ "$(ps -eo args | grep -c '[m]64_run.py.*--seeds 2000')" -eq 0 ]; do sleep 60; done
touch extra_running
echo "$(date +%H:%M:%S) extra worker start" >> progress.log
tac jobs_A.txt | tr '\n' '\0' | xargs -0 -P 1 -I{} ./dispatch.sh "{}"
rm -f extra_running
echo "$(date +%H:%M:%S) extra worker done" >> progress.log
