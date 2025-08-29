#!/bin/bash
set -e

echo "===== Starting EC2 Deployment Process ====="
echo "$(date)"

# Update from git repository
echo "===== Pulling latest changes from git ====="
git pull origin master

# Update environment variables with current EC2 DNS
echo "===== Updating environment variables ====="
PUBLIC_DNS=$(curl -s http://169.254.169.254/latest/meta-data/public-hostname)
if [ -n "$PUBLIC_DNS" ]; then
  # Create or update .env file
  grep -q "REACT_APP_API_URL" .env && \
    sed -i "s|REACT_APP_API_URL=.*|REACT_APP_API_URL=http://$PUBLIC_DNS:8000|g" .env || \
    echo "REACT_APP_API_URL=http://$PUBLIC_DNS:8000" >> .env
  
  echo "Updated API URL to http://$PUBLIC_DNS:8000"
else
  echo "Warning: Could not get EC2 public DNS"
fi

# Stop any running containers
echo "===== Stopping existing containers ====="
docker-compose down

# Build with timeout monitoring for frontend
echo "===== Building containers (with monitoring) ====="
docker-compose -f docker-compose.prod.yml build db backend
echo "Building frontend (this may take a few minutes)..."

# Start frontend build with monitoring
docker-compose -f docker-compose.prod.yml build frontend &
BUILD_PID=$!

# Set a 15-minute timeout
TIMEOUT=900
echo "Monitoring frontend build (PID: $BUILD_PID) with $TIMEOUT second timeout"
count=0
while kill -0 $BUILD_PID 2> /dev/null; do
  sleep 10
  count=$((count + 10))
  echo "Still building... ($count seconds elapsed)"
  
  if [ $count -ge $TIMEOUT ]; then
    echo "Build timeout exceeded ($TIMEOUT seconds). Killing build process."
    kill -9 $BUILD_PID
    echo "You may need to run: docker system prune -a"
    exit 1
  fi
done

# Wait for build process to complete
wait $BUILD_PID || { echo "Frontend build failed"; exit 1; }

# Start the containers
echo "===== Starting containers ====="
docker-compose -f docker-compose.prod.yml up -d

# Show running containers
echo "===== Deployment complete ====="
docker-compose ps

echo "Application deployed successfully!"
echo "Frontend: http://$PUBLIC_DNS"
echo "Backend API: http://$PUBLIC_DNS:8000"
echo "$(date)"
