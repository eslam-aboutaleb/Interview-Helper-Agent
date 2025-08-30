#!/bin/bash
# Check API endpoints

echo "===== API Endpoint Check ====="

# Define colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Define your EC2 instance
EC2_HOST="ec2-16-16-26-79.eu-north-1.compute.amazonaws.com"

# Function to check an endpoint
check_endpoint() {
  local url=$1
  local description=$2
  
  echo -e "${YELLOW}Checking $description...${NC}"
  echo "URL: $url"
  
  # Use curl to check the endpoint
  status_code=$(curl -s -o /dev/null -w "%{http_code}" $url)
  
  if [[ $status_code -ge 200 && $status_code -lt 400 ]]; then
    echo -e "${GREEN}✅ Success! Status code: $status_code${NC}"
    return 0
  else
    echo -e "${RED}❌ Failed! Status code: $status_code${NC}"
    return 1
  fi
}

# Check if curl is installed
if ! command -v curl &> /dev/null; then
  echo "curl is not installed. Installing..."
  apt-get update && apt-get install -y curl
fi

# Check various API endpoints
echo ""
check_endpoint "http://$EC2_HOST:8000" "Main API endpoint"
echo ""
check_endpoint "http://$EC2_HOST:8000/docs" "Swagger documentation"
echo ""
check_endpoint "http://$EC2_HOST:8000/api/docs" "Alternative API documentation path"
echo ""
check_endpoint "http://$EC2_HOST:8000/health" "Health check endpoint"
echo ""
check_endpoint "http://$EC2_HOST:8000/api/questions" "Questions API"
echo ""

# Check the frontend
echo -e "${YELLOW}Checking frontend...${NC}"
echo "URL: http://$EC2_HOST"
frontend_status=$(curl -s -o /dev/null -w "%{http_code}" http://$EC2_HOST)
if [[ $frontend_status -ge 200 && $frontend_status -lt 400 ]]; then
  echo -e "${GREEN}✅ Frontend is accessible! Status code: $frontend_status${NC}"
else
  echo -e "${RED}❌ Frontend is not accessible. Status code: $frontend_status${NC}"
fi

echo ""
echo "===== Common Issues and Solutions ====="
echo "1. If all endpoints failed, check if port 8000 is open in your security group"
echo "2. If some endpoints work but others don't, check API routes in your backend code"
echo "3. If you see '❌ Failed! Status code: 000', it means the connection was refused"
echo "   - This usually means port 8000 is blocked by the security group"

echo ""
echo "===== API Endpoint Check Complete ====="
