# InteliSort

## Setup
### Pre-requisites
assumes you have the following installed:
- pyenv
- poetry
- Docker
- Docker Compose
```bash
poetry install
cp .env.example .env # Copy the example environment file, then fill in the values
docker-compose up -d # Start the database
poetry run prisma generate && poetry run prisma db push
```
## Start the server
```bash
docker-compose up -d # Start the database
# EXPORT PORT=8000 or set change the $PORT variable in the command below (recommended)
PORT=8000 poetry run gunicorn -w 1 -k uvicorn.workers.UvicornWorker --bind "[::]:$PORT" app.main:app --timeout 300
# mac user & linux user can use the following command
chmod +x ./run.sh
PORT=8000 ./run.sh
```
## Build Docker Image
```bash
# docker build -t path/to/image:tag .
docker buildx build -t path/to/image:tag . --platform linux/amd64 # For multi-architecture builds, make sure to have buildx enabled
```