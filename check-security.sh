#!/bin/bash
# Quick manual check for security group and port accessibility

echo "===== Manual Security Check ====="

# Check if the backend is accessible locally
echo "Checking if backend is accessible locally..."
curl -s http://localhost:8000 || echo "❌ Backend is not accessible locally"

# Check if port 8000 is open using netcat if available
if command -v nc &> /dev/null; then
  echo "Checking if port 8000 is open..."
  nc -zv localhost 8000 || echo "❌ Port 8000 is not open locally"
fi

# Check Docker container status
echo "Checking Docker container status..."
docker ps

echo ""
echo "===== Important Notes ====="
echo "If your containers are running but you can't access them externally, you likely need to:"
echo ""
echo "1. Open port 8000 in your EC2 security group:"
echo "   - Go to AWS Console > EC2 > Security Groups"
echo "   - Select the security group attached to your instance"
echo "   - Click 'Edit inbound rules'"
echo "   - Add rule: Custom TCP, Port Range: 8000, Source: 0.0.0.0/0"
echo "   - Click 'Save rules'"
echo ""
echo "2. Make sure your backend is properly configured:"
echo "   - The backend should be listening on 0.0.0.0 (all interfaces), not just localhost"
echo "   - Check the logs for any errors: docker logs interview-prep-backend"
echo ""
echo "3. Try accessing the API at different URL paths:"
echo "   - Main backend: http://ec2-16-16-26-79.eu-north-1.compute.amazonaws.com:8000"
echo "   - Docs at: http://ec2-16-16-26-79.eu-north-1.compute.amazonaws.com:8000/docs"
echo "   - Alternative docs: http://ec2-16-16-26-79.eu-north-1.compute.amazonaws.com:8000/api/docs"
echo "   - Health check: http://ec2-16-16-26-79.eu-north-1.compute.amazonaws.com:8000/health"
echo ""
echo "===== Check Complete ====="
