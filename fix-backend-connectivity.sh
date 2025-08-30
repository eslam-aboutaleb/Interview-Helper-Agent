#!/bin/bash
# Backend connectivity fix script

echo "===== Backend Connectivity Fix ====="
echo "$(date)"

# Make sure Docker is running
if ! systemctl is-active --quiet docker; then
  echo "Docker is not running. Starting Docker..."
  sudo systemctl start docker
fi

# Fix 1: Stop and remove existing containers
echo "Stopping existing containers..."
docker-compose -f docker-compose.prod.yml down

# Fix 2: Explicitly configure the backend to listen on all interfaces
echo "Creating backend configuration override..."
mkdir -p backend_fix
cat > backend_fix/main_override.py << 'EOF'
import uvicorn
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routes import questions, stats

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Interview Prep API",
    description="API for Interview Preparation Application",
    version="1.0.0",
)

# Configure CORS to allow requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Include routers
app.include_router(questions.router, prefix="/questions", tags=["questions"])
app.include_router(stats.router, prefix="/stats", tags=["stats"])

# Root endpoint
@app.get("/")
def read_root():
    return {"message": "Welcome to the Interview Prep API"}

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    # This ensures FastAPI listens on all interfaces (0.0.0.0)
    # and is accessible from outside the container
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
EOF

# Fix 3: Update backend Dockerfile to use new main.py
cat > backend_fix/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .
COPY main_override.py main.py

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "main.py"]
EOF

# Fix 4: Create a docker-compose override for the backend
cat > backend_fix/docker-compose.override.yml << 'EOF'
version: "3.8"

services:
  backend:
    build:
      context: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://${DB_USER:-postgres}:${DB_PASSWORD:-postgres}@db:5432/${DB_NAME:-interviews}
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 5
EOF

# Copy files to their correct locations
echo "Copying configuration files..."
cp backend_fix/main_override.py backend/main_override.py
cp backend_fix/Dockerfile backend/Dockerfile
cp backend/main_override.py backend/main.py

# Fix 5: Make sure the EC2 security group allows traffic on port 8000
echo ""
echo "IMPORTANT: Make sure port 8000 is open in your EC2 security group."
echo "You can add a rule through the AWS Console: EC2 > Security Groups > [Your SG] > Edit inbound rules"
echo "Add a rule with: Type: Custom TCP, Port: 8000, Source: 0.0.0.0/0"
echo ""

# Fix 6: Restart with the new configuration
echo "Building and starting containers with fixes..."
docker-compose -f docker-compose.prod.yml build backend
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to start
echo "Waiting for services to start..."
sleep 10

# Check the status
echo "Checking container status..."
docker ps

# Check backend logs
echo "Backend logs:"
docker logs interview-prep-backend

echo "===== Backend Connectivity Fix Complete ====="
echo "Try accessing the backend API at: http://ec2-16-16-26-79.eu-north-1.compute.amazonaws.com:8000/docs"
echo "$(date)"
