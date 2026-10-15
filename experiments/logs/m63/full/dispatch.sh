#!/bin/bash
# line format: J:<arm|cond|seeds>  or  C:<tag|cmd>
case "$1" in J:*) exec ./run_job.sh "${1#J:}";; C:*) exec ./run_cmd.sh "${1#C:}";; esac
