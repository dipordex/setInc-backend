
# Set Inc Back End

## [Project deployment guide](./docs/deploy.md)


# cmd 


```
docker compose --env-file .env -f docker-compose.yml up --build
```

# To gernate Swagger 

```py
python manage.py generate_openapi_schema
```


# websocket 

```
uvicorn setinc.asgi:application --host 0.0.0.0 --port 8000 --reload
```
# fcm tst Curl

```


# 🔐 Store your FCM device token
export FCM_TOKEN="fbVOL7o2Th-Ou1-bBZNEpy:APA91bFjOlXXzRrcK-oV8K7gGuONXVE9cI06-oJJLXPAMcBMiLGEgOAAf79C0T1NyyzvQIwT7nZyHSxL8i4xXYO-X5_PsW2mhfdlBTFcrJF6Nx5k1HFinjU"

# 🔧 Store your Firebase project ID
export FCM_PROJECT="712736621517"

# 🔑 Store access token
export ACCESS_TOKEN=$(gcloud auth application-default print-access-token)


curl -X POST \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "token": "'"$FCM_TOKEN"'",
      "notification": {
        "title": "🔥 Task Tracker",
        "body": "Notification from Cloud Shell variables!"
      }
    }
  }' \
  https://fcm.googleapis.com/v1/projects/$FCM_PROJECT/messages:send
````