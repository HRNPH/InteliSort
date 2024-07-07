#!/bin/bash
docker-compose up -d
export PORT=8000
poetry run gunicorn -w 1 -k uvicorn.workers.UvicornWorker --bind "[::]:$PORT" app.main:app --timeout 300