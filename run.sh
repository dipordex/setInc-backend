#!/bin/env bash

# Retrieve secrets from AWS & export to environment
# python3 retrieve-secrets.py .aws-secrets.env 2>&1
# export $(grep -v '^#' .aws-secrets.env | xargs) 2>&1

# python retrieve_google_keys.py

python3 manage.py migrate
# python3 manage.py loaddata fixture.yaml
python3 manage.py collectstatic --noinput

# Run server
gunicorn --workers 3 --timeout 600 --bind 0.0.0.0:8000 setinc.wsgi:application
