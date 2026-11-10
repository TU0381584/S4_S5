#!/bin/bash
# wait for the M102 pilot, apply the pre-registered selection, write the M103 jobs, run M103
R=/home/kmanojp/oranslice_rig
until grep -qE "ALL DONE" $R/experiments/logs/m102/done.txt 2>/dev/null; do sleep 60; done
if grep -qE "exit [1-9]" $R/experiments/logs/m102/done.txt; then echo "pilot had a failed job; M103 not started $(date +%T)" >> $R/experiments/logs/m103/done.txt; exit 1; fi
cd $R/framework
../venv/bin/python ../experiments/scripts/m102_select.py --out ../experiments/results/m102/selection.json > ../experiments/logs/m103/selection.out 2>&1 || { echo "selection failed $(date +%T)" >> ../experiments/logs/m103/done.txt; exit 1; }
../venv/bin/python ../experiments/scripts/m103_analysis.py --jobs ../experiments/logs/m103/phase1.txt >> ../experiments/logs/m103/selection.out 2>&1
cd $R
(nohup setsid experiments/logs/m103/gzip_loop.sh > experiments/logs/m103/gzip.out 2>&1 < /dev/null &)
experiments/logs/m103/run_all.sh
