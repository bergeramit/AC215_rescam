#!/bin/bash

set -e

IMAGE_NAME="ml-model"
PROJECT_ROOT="$(cd ../../ && pwd)"

cd "$PROJECT_ROOT"

# Check if image exists, only build if it doesn't
if docker image inspect $IMAGE_NAME >/dev/null 2>&1; then
    echo "✅ Docker image exists, skipping build..."
else
    echo "🔨 Building Docker image (this may take a few minutes)..."
    docker build -t $IMAGE_NAME -f src/models/Dockerfile .
fi

# Mount credentials and run interactively
echo "🚀 Starting Docker container..."
docker run --rm -ti \
    -v "$HOME/.config/gcloud:/home/app/.config/gcloud:ro" \
    -e GOOGLE_APPLICATION_CREDENTIALS="/home/app/.config/gcloud/application_default_credentials.json" \
    -v "$PROJECT_ROOT/src/models:/app/workspace:rw" \
    -w /app \
    $IMAGE_NAME \
    /bin/bash