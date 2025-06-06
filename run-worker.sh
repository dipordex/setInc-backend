#!/bin/env bash

# Retrieve secrets from AWS & export to environment
python retrieve-secrets.py .aws-secrets.env 2>&1
export $(grep -v '^#' .aws-secrets.env | xargs) 2>&1

python retrieve_google_keys.py

export DRAMATIQ_DEFAULT_QUEUE
python manage.py rundramatiq --queues="$DRAMATIQ_DEFAULT_QUEUE"
#