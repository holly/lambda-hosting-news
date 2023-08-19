#!/usr/bin/env bash

set -e
set -o pipefail
set -C


APP=$(basename $PWD)
ZIPFILE=$PWD/lambda.zip

FUNCTION_DESCRIPTION="hosting news notification"
ENV_FILE="$PWD/.env"

export AWS_PAGER=""
if [ -z "$AWS_DEFAULT_REGION"  ]; then
    export AWS_DEFAULT_REGION=us-east-1
fi
if [ -z "$AWS_DEFAULT_PROFILE"  ]; then
    export AWS_DEFAULT_PROFILE=default
fi
if [ -z "$LAMBDA_FUNCTION_NAME"  ]; then
    LAMBDA_FUNCTION_NAME=$(echo $APP | sed -e 's/^lambda\-//')
fi

zip -r $ZIPFILE lambda_function.py

if [[ -f "$ENV_FILE" ]]; then
    aws lambda update-function-configuration  --function-name $LAMBDA_FUNCTION_NAME --environment Variables={$(cat $ENV_FILE | tr -s "\n" | tr '\n' ',' | sed s/,$//)}
fi

aws lambda update-function-code \
--function-name $LAMBDA_FUNCTION_NAME \
--zip-file fileb://$ZIPFILE 

rm $ZIPFILE
