#!/bin/bash
# Backend connectivity troubleshooting script

echo "===== Backend Connectivity Troubleshooting ====="
echo "$(date)"

# Check if Docker is running
echo "Checking Docker status..."
if ! systemctl is-active --quiet docker; then
  echo "❌ Docker is not running. Starting Docker..."
  sudo systemctl start docker
else
  echo "✅ Docker is running"
fi

# Check if the containers are running
echo "Checking container status..."
docker ps
echo ""

# Check if the backend container is running
echo "Checking backend container specifically..."
if docker ps | grep -q "interview-prep-backend"; then
  echo "✅ Backend container is running"
else
  echo "❌ Backend container is not running"
  
  # Check if the container exists but is not running
  if docker ps -a | grep -q "interview-prep-backend"; then
    echo "Backend container exists but is not running. Checking logs..."
    docker logs interview-prep-backend
  else
    echo "Backend container doesn't exist at all."
  fi
fi

# Check network connectivity
echo "Checking internal network connectivity..."
docker exec -it interview-prep-backend curl -s http://localhost:8000 || echo "❌ Internal connectivity check failed"

# Check EC2 security groups
echo "Checking if port 8000 is open in the security group..."
# This requires AWS CLI to be set up
if command -v aws &> /dev/null; then
  INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
  aws ec2 describe-instances --instance-ids $INSTANCE_ID --query "Reservations[*].Instances[*].SecurityGroups[*]" --output json
else
  echo "AWS CLI not installed. Please check security groups manually in AWS Console."
  echo "Make sure port 8000 is open for inbound traffic."
fi

# Check the environment variables
echo "Checking backend environment variables..."
docker exec interview-prep-backend env || echo "❌ Cannot check environment variables"

# Check if database is accessible from backend
echo "Checking database connectivity from backend..."
docker exec interview-prep-backend ping -c 2 db || echo "❌ Cannot ping database from backend"

# View the backend logs
echo "Viewing backend container logs..."
docker logs interview-prep-backend --tail 50

# Restart backend container
echo "Would you like to restart the backend container? (y/n)"
read -p "> " answer
if [ "$answer" = "y" ]; then
  echo "Restarting backend container..."
  docker restart interview-prep-backend
  echo "Waiting for container to start..."
  sleep 5
  echo "New backend container logs:"
  docker logs interview-prep-backend --tail 20
fi

# Suggestion for fixing common issues
echo ""
echo "===== Possible Solutions ====="
echo "1. Ensure port 8000 is open in EC2 security group"
echo "2. Check backend logs for specific errors"
echo "3. Verify database connectivity"
echo "4. Check environment variables (especially DATABASE_URL and GEMINI_API_KEY)"
echo "5. Try redeploying with docker-compose -f docker-compose.prod.yml up -d --build"
echo ""

echo "===== Troubleshooting Complete ====="
