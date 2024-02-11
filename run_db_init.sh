#!/bin/bash
e
docker-compose up -d
poetry run prisma generate && poetry run prisma db push