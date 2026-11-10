#!/bin/bash
# one M103 job: name|ENV=VAL ...|command (cwd framework/)
line="$1"; name="${line%%|*}"; rest="${line#*|}"; envs="${rest%%|*}"; cmd="${rest#*|}"
cd /home/kmanojp/oranslice_rig/framework
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
[ -n "$envs" ] && export $envs
../venv/bin/python3 $cmd > ../experiments/logs/m103/$name.log 2>&1
echo "$name exit $? $(date '+%H:%M:%S')" >> ../experiments/logs/m103/done.txt
