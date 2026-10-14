#!/bin/bash
cd /home/kmanojp/oranslice_rig/experiments/logs/m62
run() { tr '\n' '\0' < "$1" | xargs -0 -P "$2" -I{} ./run_cmd.sh "{}"; }
echo "$(date +%H:%M:%S) start phase3a" >> progress.log
run jobs_p3a.txt 2 &
A=$!
until grep -q 'done p2_rep_axiom_1000' progress.log && grep -q 'done p2_rep_axiom_1005' progress.log && grep -q 'done p2_rep_indep' progress.log; do sleep 60; done
echo "$(date +%H:%M:%S) start phase3b" >> progress.log
run jobs_p3b.txt 2 &
B=$!
until grep -q 'ALL PHASE2 DONE' progress.log; do sleep 60; done
echo "$(date +%H:%M:%S) start phase3c" >> progress.log
run jobs_p3c.txt 2
wait $A $B
cd /home/kmanojp/oranslice_rig
for d in m62_m4 m62_m4_replication; do ./venv/bin/python3 experiments/scripts/m62_m4_merge.py experiments/results/$d >> experiments/logs/m62/progress.log 2>&1; done
echo "$(date +%H:%M:%S) ALL PHASE3 DONE" >> experiments/logs/m62/progress.log
