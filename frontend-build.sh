#!/bin/bash

# Script to build the frontend with improved monitoring and error handling

echo "Starting frontend build with optimized settings..."

# Set build timeout (minutes)
TIMEOUT=15

# Remove any existing container to start fresh
echo "Removing any existing frontend containers..."
docker rm -f interview-prep-frontend 2>/dev/null

# Build with timeout and resource monitoring
echo "Building frontend container with ${TIMEOUT} minute timeout..."
timeout ${TIMEOUT}m docker-compose -f docker-compose.prod.yml build frontend

# Check build status
if [ $? -eq 124 ]; then
  echo "ERROR: Build timed out after ${TIMEOUT} minutes!"
  echo "Try building with increased memory or on a machine with more resources."
  exit 1
elif [ $? -ne 0 ]; then
  echo "ERROR: Build failed!"
  exit 1
else
  echo "Frontend build completed successfully!"
  echo "Starting services..."
  docker-compose -f docker-compose.prod.yml up -d
fi
