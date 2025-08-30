#!/bin/bash
# Quick fix for database connection issues

echo "===== Quick Database Connection Fix ====="

# Create .env file with proper database credentials
echo "Creating .env file with correct database credentials..."
cat > .env << 'EOF'
# Database credentials
DB_NAME=interviews
DB_USER=postgres
DB_PASSWORD=postgres
POSTGRES_PASSWORD=postgres

# API key
GEMINI_API_KEY=your-gemini-api-key-here

# Frontend configuration
REACT_APP_API_URL=http://ec2-16-16-26-79.eu-north-1.compute.amazonaws.com:8000
EOF

echo ".env file created."
echo "Please edit the .env file to add your actual Gemini API key if needed."

# Stop all containers
echo "Stopping all containers..."
docker-compose -f docker-compose.prod.yml down

# Remove database volume to start fresh
echo "Removing database volume for clean start..."
docker volume rm project_postgres_data 2>/dev/null || echo "No postgres volume to remove."

# Rebuild and restart all containers
echo "Rebuilding and restarting containers..."
docker-compose -f docker-compose.prod.yml up -d --build

echo "===== Fix Complete ====="
echo "Wait a few moments for the containers to start properly."
echo "Then try accessing your application at:"
echo "Frontend: http://ec2-16-16-26-79.eu-north-1.compute.amazonaws.com"
echo "Backend API: http://ec2-16-16-26-79.eu-north-1.compute.amazonaws.com:8000"
echo "API Documentation: http://ec2-16-16-26-79.eu-north-1.compute.amazonaws.com:8000/api/docs or /docs"
