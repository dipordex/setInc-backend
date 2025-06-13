
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