#!/usr/bin/env bash
set -euo pipefail

# Simple deploy script for EC2 + Docker Compose
# Usage on the host: PLACE this repo at /opt/performance-testing-platform and run as the deploy user

COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.prod.yml}
APP_DIR=${APP_DIR:-/opt/performance-testing-platform}
SERVICE_NAMES=${SERVICE_NAMES:-"backend loadforge nginx"}

cd "$APP_DIR"

# Pull images (in case images are hosted in a registry)
docker-compose -f "$COMPOSE_FILE" pull --ignore-pull-failures

# Recreate services
docker-compose -f "$COMPOSE_FILE" up -d --remove-orphans $SERVICE_NAMES

# Optional: prune unused images
docker image prune -f

echo "Deploy complete"
