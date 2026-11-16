#!/bin/bash
# one M111 job: name|ENV=VAL ...|command (cwd framework/); restart-safe
line="$1"; name="${line%%|*}"; rest="${line#*|}"; envs="${rest%%|*}"; cmd="${rest#*|}"
cd /home/kmanojp/oranslice_rig/framework
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
[ -n "$envs" ] && export $envs
grep -q "^$name exit 0 " ../experiments/logs/m111/done.txt 2>/dev/null && exit 0
../venv/bin/python3 $cmd > ../experiments/logs/m111/$name.log 2>&1
echo "$name exit $? $(date '+%H:%M:%S')" >> ../experiments/logs/m111/done.txt
