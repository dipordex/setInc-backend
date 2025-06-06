#!/bin/env bash

# Retrieve secrets from AWS & export to environment
python retrieve-secrets.py .aws-secrets.env 2>&1
export $(grep -v '^#' .aws-secrets.env | xargs) 2>&1

python manage.py migrate
# python manage.py loaddata fixture.yaml
python manage.py collectstatic --noinput
