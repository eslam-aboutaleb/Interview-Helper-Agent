#!/bin/bash
# This script helps diagnose common issues with EC2 deployment
# Run with: bash ec2-troubleshoot.sh

echo "===== EC2 Deployment Troubleshooting ====="
echo "$(date)"

# Step 1: Check if running on EC2
echo "===== Checking if running on EC2 ====="
EC2_METADATA=$(curl -s --connect-timeout 2 http://169.254.169.254/latest/meta-data/)
if [ $? -ne 0 ]; then
  echo "ERROR: Not running on EC2 or metadata service not accessible"
  echo "This script is designed to run on EC2 instances"
else
  echo "SUCCESS: Running on EC2"
  echo "Instance metadata available"
fi

# Step 2: Check Docker status
echo "===== Checking Docker status ====="
if command -v docker &> /dev/null; then
  echo "Docker is installed"
  
  # Check if Docker daemon is running
  if sudo systemctl is-active --quiet docker; then
    echo "SUCCESS: Docker service is running"
  else
    echo "ERROR: Docker service is not running"
    echo "Try: sudo systemctl start docker"
  fi
  
  # Check Docker version
  echo "Docker version:"
  docker --version
  
  # Check if current user can run Docker
  if docker ps &> /dev/null; then
    echo "SUCCESS: Current user can run Docker commands"
  else
    echo "ERROR: Current user cannot run Docker commands"
    echo "Your user may not be in the docker group"
    echo "Run: sudo usermod -aG docker $USER"
    echo "Then log out and log back in"
  fi
else
  echo "ERROR: Docker is not installed"
  echo "Run the ec2-setup.sh script to install Docker"
fi

# Step 3: Check Docker Compose status
echo "===== Checking Docker Compose status ====="
if command -v docker-compose &> /dev/null; then
  echo "SUCCESS: Docker Compose is installed"
  echo "Docker Compose version:"
  docker-compose --version
else
  echo "ERROR: Docker Compose is not installed"
  echo "Run the ec2-setup.sh script to install Docker Compose"
fi

# Step 4: Check project files
echo "===== Checking project files ====="
if [ -f "docker-compose.prod.yml" ]; then
  echo "SUCCESS: docker-compose.prod.yml exists"
else
  echo "ERROR: docker-compose.prod.yml not found"
  echo "Make sure you're in the correct directory"
  echo "Current directory: $(pwd)"
fi

if [ -f ".env" ]; then
  echo "SUCCESS: .env file exists"
  # Check for required variables
  if grep -q "REACT_APP_API_URL" .env && grep -q "DATABASE_URL" .env; then
    echo "Required environment variables found in .env"
  else
    echo "WARNING: Some required environment variables might be missing in .env"
  fi
else
  echo "ERROR: .env file not found"
  echo "Create a .env file with required environment variables"
fi

# Step 5: Check deployment scripts
echo "===== Checking deployment scripts ====="
if [ -f "ec2-deploy.sh" ]; then
  echo "SUCCESS: ec2-deploy.sh exists"
  if [ -x "ec2-deploy.sh" ]; then
    echo "ec2-deploy.sh is executable"
  else
    echo "WARNING: ec2-deploy.sh is not executable"
    echo "Run: chmod +x ec2-deploy.sh"
  fi
else
  echo "ERROR: ec2-deploy.sh not found"
fi

# Step 6: Check system resources
echo "===== Checking system resources ====="
echo "CPU info:"
cat /proc/cpuinfo | grep "model name" | head -1
echo "Memory info:"
free -h
echo "Disk space:"
df -h | grep -E "Filesystem|/$"
echo "Swap space:"
swapon --show

# Step 7: Suggest next steps
echo "===== Troubleshooting complete ====="
echo "Based on the checks, here are recommendations:"
echo ""
echo "1. If Docker is not installed or not running:"
echo "   Run the ec2-setup.sh script to set up your EC2 instance"
echo ""
echo "2. If you can't run Docker commands without sudo:"
echo "   sudo usermod -aG docker $USER"
echo "   Then log out and log back in"
echo ""
echo "3. If environment variables are not set correctly:"
echo "   Update your .env file with the correct EC2 public DNS/IP"
echo ""
echo "4. For smaller instances that may have memory issues during build:"
echo "   Use the --prebuilt option: ./ec2-deploy.sh --prebuilt"
echo "   Or build with monitoring: ./frontend-build.sh"
echo ""
echo "$(date)"
