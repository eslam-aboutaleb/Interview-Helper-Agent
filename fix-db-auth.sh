#!/bin/bash
# Fix database authentication issues

echo "===== Database Authentication Fix ====="
echo "$(date)"

# Stop all containers
echo "Stopping all containers..."
docker-compose down

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
  echo "Creating .env file..."
  cat > .env << 'EOF'
# Database Configuration
DB_NAME=interviews
DB_USER=postgres
DB_PASSWORD=postgres
POSTGRES_PASSWORD=postgres

# API Configuration
GEMINI_API_KEY=your-gemini-api-key-here

# Frontend Configuration
REACT_APP_API_URL=http://localhost:8000
EOF
  echo ".env file created. Please update with your actual Gemini API key."
else
  # Check if DB password variables exist
  if ! grep -q "POSTGRES_PASSWORD" .env; then
    echo "Adding POSTGRES_PASSWORD to .env file..."
    echo "POSTGRES_PASSWORD=postgres" >> .env
    echo "Added POSTGRES_PASSWORD variable to .env file."
  fi
fi

# Create a docker-compose override file
echo "Creating docker-compose override file to fix DB authentication..."
cat > docker-compose.override.yml << 'EOF'
version: "3.8"

services:
  db:
    environment:
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgres}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./db/init.sql:/docker-entrypoint-initdb.d/init.sql
    command: ["postgres", "-c", "log_statement=all"]
  
  backend:
    environment:
      - DATABASE_URL=postgresql://${DB_USER:-postgres}:${POSTGRES_PASSWORD:-postgres}@db:5432/${DB_NAME:-interviews}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    depends_on:
      db:
        condition: service_healthy
EOF

echo "Docker Compose override file created."

# Clean up Docker volumes to ensure fresh database
echo "Would you like to clean up the database volume to start fresh? (y/n)"
read -p "> " answer
if [ "$answer" = "y" ]; then
  echo "Removing database volume..."
  docker-compose down -v
  docker volume rm $(docker volume ls -q | grep postgres_data) 2>/dev/null || echo "No postgres volume to remove."
fi

# Build and start containers
echo "Building and starting containers..."
docker-compose up -d --build

# Show logs for troubleshooting
echo "Showing logs for troubleshooting (Ctrl+C to stop)..."
docker-compose logs -f

echo "===== Database Authentication Fix Complete ====="
