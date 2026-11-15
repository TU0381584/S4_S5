#!/bin/bash
# one M109 job: name|ENV=VAL ...|command (cwd framework/)
line="$1"; name="${line%%|*}"; rest="${line#*|}"; envs="${rest%%|*}"; cmd="${rest#*|}"
cd /home/kmanojp/oranslice_rig/framework
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
[ -n "$envs" ] && export $envs
grep -q "^$name exit 0 " ../experiments/logs/m109/done.txt 2>/dev/null && exit 0     # finished before a restart
../venv/bin/python3 $cmd > ../experiments/logs/m109/$name.log 2>&1
echo "$name exit $? $(date '+%H:%M:%S')" >> ../experiments/logs/m109/done.txt
