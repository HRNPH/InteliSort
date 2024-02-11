# Use a smaller base image (Python slim variant)
FROM python:3.12.2-slim-bullseye as builder
ENV DEBIAN_FRONTEND=noninteractive

# Configure Poetry
ENV POETRY_VERSION=1.7.1
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VENV=/opt/poetry-venv
ENV POETRY_CACHE_DIR=/opt/.cache

# Install system dependencies required for build
# Install poetry separated from system interpreter
RUN apt-get update && apt-get install -y --no-install-recommends \
	&& python3 -m venv $POETRY_VENV \
	&& $POETRY_VENV/bin/pip install -U pip setuptools wheel \
	&& $POETRY_VENV/bin/pip install poetry==$POETRY_VERSION

# Add `poetry` to PATH
ENV PATH="${PATH}:${POETRY_VENV}/bin"

# Copy only files required for pip install
WORKDIR /tmp/build
COPY poetry.lock pyproject.toml ./

# Install dependencies including build dependencies
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes \
    && pip install --prefix=/install --no-warn-script-location -r requirements.txt

# Start a new stage from a smaller image
FROM python:3.12.2-slim-bullseye

# Install ffmpeg in the runtime image
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

# Copy installed python packages from builder stage
COPY --from=builder /install /usr/local

# Copy the application code to the container
WORKDIR /backend
COPY ./app /backend/app
COPY ./prisma /backend/prisma

# Generate Prisma client
RUN python3 -m prisma generate

# Listen to $PORT environment variable
CMD gunicorn -w 1 -k uvicorn.workers.UvicornWorker --bind [::]:$PORT app.main:app --timeout 300