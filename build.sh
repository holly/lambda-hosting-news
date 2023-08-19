#!/usr/bin/env bash

set -e
set -u
set -o pipefail
set -C


APP=$(basename $PWD | sed -e 's/^lambda\-//')
TAG="$USER/$APP"
docker build -t ${TAG}:latest  .
