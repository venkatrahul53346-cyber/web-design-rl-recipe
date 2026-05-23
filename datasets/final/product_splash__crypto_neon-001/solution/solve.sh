#!/bin/bash
# Oracle solver: copy the ground-truth website verbatim into /app/.
# Use `cp -a /dir/.` form so the copy succeeds even if a future template
# adds extra files (images, fonts) under ground_truth/.
set -euo pipefail
cp -a /solution/ground_truth/. /app/
echo "oracle: ground truth copied to /app/"
