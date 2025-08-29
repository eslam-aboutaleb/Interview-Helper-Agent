#!/bin/bash
set -e

echo "===== Starting EC2 Deployment Process ====="
echo "$(date)"

# Default options
SKIP_FRONTEND_BUILD=false
PREBUILT_MODE=false

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
  case $1 in
    --skip-frontend) SKIP_FRONTEND_BUILD=true ;;
    --prebuilt) PREBUILT_MODE=true ;;
    *) echo "Unknown parameter: $1"; exit 1 ;;
  esac
  shift
done

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
docker-compose -f docker-compose.prod.yml down

# Build backend and database
echo "===== Building backend and database ====="
docker-compose -f docker-compose.prod.yml build db backend

# Handle frontend build based on options
if [ "$SKIP_FRONTEND_BUILD" = true ]; then
  echo "===== Skipping frontend build as requested ====="
elif [ "$PREBUILT_MODE" = true ]; then
  echo "===== Using pre-built frontend mode ====="
  echo "Make sure you've built and pushed the frontend image to a registry"
else
  # Build frontend with monitoring
  echo "===== Building frontend (this may take several minutes) ====="
  
  # Free up system resources before building
  echo "Cleaning up Docker system to free resources..."
  docker system prune -f
  
  # Start frontend build with resource monitoring
  docker-compose -f docker-compose.prod.yml build frontend &
  BUILD_PID=$!
  
  # Set a 20-minute timeout (1200 seconds)
  TIMEOUT=1200
  echo "Monitoring frontend build (PID: $BUILD_PID) with $TIMEOUT second timeout"
  
  # Monitor system resources during build
  count=0
  while kill -0 $BUILD_PID 2> /dev/null; do
    sleep 15
    count=$((count + 15))
    
    # Print build status with resource usage
    echo "---------------------------------------------"
    echo "Build in progress... ($count seconds elapsed)"
    echo "Memory usage:"
    free -h
    echo "CPU usage:"
    top -bn1 | head -5
    echo "Docker disk usage:"
    docker system df
    echo "---------------------------------------------"
    
    if [ $count -ge $TIMEOUT ]; then
      echo "Build timeout exceeded ($TIMEOUT seconds). Killing build process."
      kill -9 $BUILD_PID
      echo "Consider using --skip-frontend or --prebuilt options"
      echo "You may need to run: docker system prune -a"
      exit 1
    fi
  done
  
  # Wait for build process to complete
  if wait $BUILD_PID; then
    echo "Frontend build completed successfully!"
  else
    echo "Frontend build failed with exit code $?"
    echo "Consider using --skip-frontend or --prebuilt options"
    exit 1
  fi
fi

# Start the containers
echo "===== Starting containers ====="
docker-compose -f docker-compose.prod.yml up -d

# Show running containers
echo "===== Deployment complete ====="
docker-compose -f docker-compose.prod.yml ps

echo "Application deployed successfully!"
echo "Frontend: http://$PUBLIC_DNS"
echo "Backend API: http://$PUBLIC_DNS:8000"
echo "$(date)"
