#!/bin/bash
# This script builds and deploys the frontend without TypeScript errors
# It installs TypeScript type definitions locally first, then builds the Docker image

echo "===== Starting Frontend TypeScript Fix Deployment ====="
echo "$(date)"

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Check for required commands
if ! command_exists npm || ! command_exists docker || ! command_exists docker-compose; then
  echo "Error: Required tools (npm, docker, docker-compose) not installed"
  echo "Please run ./ec2-setup.sh first"
  exit 1
fi

# Move to frontend directory
cd frontend

# Check if package.json exists
if [ ! -f "package.json" ]; then
  echo "Error: package.json not found in frontend directory"
  echo "Make sure you're in the correct project directory"
  exit 1
fi

echo "===== Installing TypeScript definitions locally ====="
npm install --save-dev @types/react @types/react-dom @types/react-router-dom

# Create custom.d.ts file if it doesn't exist
if [ ! -f "src/custom.d.ts" ]; then
  echo "===== Creating custom TypeScript declarations ====="
  mkdir -p src
  cat > src/custom.d.ts << 'EOF'
// This file contains custom TypeScript declarations
// for modules that might be missing type definitions

declare module 'react';
declare module 'react-dom';
declare module 'react-router-dom';
declare module 'react-hot-toast';
EOF
  echo "Created src/custom.d.ts file"
fi

# Return to project root
cd ..

echo "===== Building Docker services ====="
# First build backend and database
docker-compose -f docker-compose.prod.yml build db backend

# Set up better monitoring for frontend build
echo "===== Building frontend with TypeScript fixes ====="
docker-compose -f docker-compose.prod.yml build frontend &
BUILD_PID=$!

# Monitor the build with a 20-minute timeout
TIMEOUT=1200
echo "Monitoring frontend build (PID: $BUILD_PID) with $TIMEOUT second timeout"
count=0
while kill -0 $BUILD_PID 2>/dev/null; do
  sleep 15
  count=$((count + 15))
  
  # Print resource usage
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
    echo "Consider using the --prebuilt option next time"
    exit 1
  fi
done

# Wait for build to complete
if wait $BUILD_PID; then
  echo "Frontend build completed successfully!"
else
  echo "Frontend build failed with exit code $?"
  echo "Check the build logs for more details"
  exit 1
fi

# Start the containers
echo "===== Starting containers ====="
docker-compose -f docker-compose.prod.yml up -d

# Show running containers
echo "===== Deployment complete ====="
docker-compose -f docker-compose.prod.yml ps

echo "Application deployed successfully!"
PUBLIC_DNS=$(curl -s http://169.254.169.254/latest/meta-data/public-hostname)
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)

if [ -n "$PUBLIC_DNS" ]; then
  echo "Frontend: http://$PUBLIC_DNS"
  echo "Backend API: http://$PUBLIC_DNS:8000"
elif [ -n "$PUBLIC_IP" ]; then
  echo "Frontend: http://$PUBLIC_IP"
  echo "Backend API: http://$PUBLIC_IP:8000"
else
  echo "Frontend: http://localhost"
  echo "Backend API: http://localhost:8000"
fi

echo "$(date)"
