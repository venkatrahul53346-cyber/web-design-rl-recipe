#!/bin/bash
# Verifier entry point. Runs grade.py; falls back to reward 0 on crash.
set -uo pipefail
mkdir -p /logs/verifier

set +e
python3 /tests/grade.py 2>&1 | tee /logs/verifier/grader.log
exit_code=$?
set -e

if [ ! -f /logs/verifier/reward.json ] && [ ! -f /logs/verifier/reward.txt ]; then
    echo "WARNING: grader produced no reward file (exit $exit_code) — defaulting to 0"
    echo 0 > /logs/verifier/reward.txt
fi

exit 0
