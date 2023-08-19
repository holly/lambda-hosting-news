#!/usr/bin/env bash

set -e
set -o pipefail
set -C


APP=$(basename $PWD | sed -e 's/^lambda\-//')
TAG="$USER/$APP"

DOCKER_OPT=""
ENV_FILE=$PWD/.env

if [[ -f "$ENV_FILE" ]]; then
    DOCKER_OPT="--env-file $ENV_FILE"
fi
if [[ -d "$PWD/data" ]]; then
    DOCKER_OPT="$DOCKER_OPT --mount type=bind,src=$PWD/data,dst=/data"
fi
docker run --rm $DOCKER_OPT -p 9000:8080 -it $TAG:latest 
