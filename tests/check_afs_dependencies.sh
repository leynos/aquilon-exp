#!/bin/bash

set -euo pipefail

BASEDIR=$(dirname "$(dirname "$0")")


SERVER_DEPS=$(awk -F'["'\'']' '/^[^#]*ms.version.addpkg/ {print $2}' $BASEDIR/lib/aquilon/worker/depends.py)
CLIENT_DEPS=$(awk -F'["'\'']' '/^[^#]*ms.version.addpkg/ {print $2}' $BASEDIR/lib/aquilon/client/depends.py)

RING1_SUBSCRIPTIONS=$(vms display subscription any python -quiet -- -type r1cell | awk '{print $4}')

exit_code=0
for dep in $CLIENT_DEPS; do
  if ! echo $RING1_SUBSCRIPTIONS | grep -q $dep; then
    echo "ERROR: Client dependency '$dep' is not subscribed to in ring1"
    exit_code=1
  fi
done

for dep in $SERVER_DEPS; do
  if ! echo $RING1_SUBSCRIPTIONS | grep -q $dep; then
    echo "INFO: Server dependency '$dep' is not subscribed to in ring1.  This is ok as the server does not run on ring1 cells."
  fi
done

exit $exit_code