#!/bin/env bash

# Retrieve secrets from AWS & export to environment
# python3 retrieve-secrets.py .aws-secrets.env 2>&1
# export $(grep -v '^#' .aws-secrets.env | xargs) 2>&1

# python retrieve_google_keys.py

#!/bin/env bash

# Retrieve secrets from AWS & export to environment
# python3 retrieve-secrets.py .aws-secrets.env 2>&1
# export $(grep -v '^#' .aws-secrets.env | xargs) 2>&1

# python retrieve_google_keys.py

python manage.py migrate
# python3 manage.py loaddata fixture.yaml
python manage.py collectstatic --noinput


# Run with ASGI for Socket.IO support
# START WITH UVICORN INSTEAD OF GUNICORN
exec uvicorn setinc.asgi:application \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --timeout-keep-alive 60

export DRAMATIQ_DEFAULT_QUEUE
python manage.py rundramatiq --queues="$DRAMATIQ_DEFAULT_QUEUE"