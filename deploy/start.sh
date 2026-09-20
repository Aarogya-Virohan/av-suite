#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f ".env" ]; then
    echo "Error: .env file not found in $SCRIPT_DIR."
    echo "Please copy the template and configure your production values:"
    echo "  cp .env.example .env"
    exit 1
fi

echo "Starting AV Suite self-hosted deployment..."

if docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker-compose"
else
    echo "Error: Neither 'docker compose' nor 'docker-compose' was found."
    exit 1
fi

$DOCKER_COMPOSE_CMD up -d --build

echo ""
echo "=== Deployment Successfully Launched ==="
echo "Application running via reverse proxy on: http://localhost:${HOST_PORT:-80}"
echo "API Documentation: http://localhost:${HOST_PORT:-80}/docs"
echo "To view logs: $DOCKER_COMPOSE_CMD logs -f"
echo "To stop: ./stop.sh"
