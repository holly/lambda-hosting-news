#!/usr/bin/env bash

set -e
set -u
set -o pipefail
set -C

curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{}'
