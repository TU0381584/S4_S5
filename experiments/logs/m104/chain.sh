#!/bin/bash
# start M104 once M103 has finished (any outcome is reported; a failed M103 job does not block M104)
R=/home/kmanojp/oranslice_rig
until grep -qE "ALL DONE|failed|not started" $R/experiments/logs/m103/done.txt 2>/dev/null; do sleep 60; done
cd $R
(nohup setsid experiments/logs/m104/gzip_loop.sh > experiments/logs/m104/gzip.out 2>&1 < /dev/null &)
experiments/logs/m104/run_all.sh
