#!/bin/bash
# Comprehensive database fix script

echo "===== Comprehensive Database Fix ====="
echo "$(date)"

# Make sure Docker is running
if ! systemctl is-active --quiet docker; then
  echo "Docker is not running. Starting Docker..."
  sudo systemctl start docker
fi

# Create .env file with correct database settings
echo "Creating .env file..."
cat > .env << 'EOF'
# Database configuration
DB_NAME=interview_prep
DB_USER=postgres
DB_PASSWORD=password
POSTGRES_PASSWORD=password
POSTGRES_DB=interview_prep

# API Key
GEMINI_API_KEY=your-gemini-api-key-here

# Frontend configuration
REACT_APP_API_URL=http://ec2-16-16-26-79.eu-north-1.compute.amazonaws.com:8000
EOF

# Confirm database name in docker-compose.yml
echo "Checking docker-compose.yml for consistency..."
if ! grep -q "POSTGRES_DB: interview_prep" docker-compose.yml; then
  echo "Warning: docker-compose.yml may not have consistent database name!"
  echo "Please check and update manually if needed."
fi

# Check the backend DATABASE_URL in docker-compose.yml
if ! grep -q "postgresql://postgres:password@db:5432/interview_prep" docker-compose.yml; then
  echo "Warning: docker-compose.yml may not have consistent DATABASE_URL!"
  echo "Please check and update manually if needed."
fi

# Create a helper script to initialize the database
echo "Creating database initialization script..."
mkdir -p db-scripts

cat > db-scripts/init-database.sql << 'EOF'
-- Drop database if it exists and recreate it
DROP DATABASE IF EXISTS interview_prep;
CREATE DATABASE interview_prep;

-- Connect to the interview_prep database
\c interview_prep;

-- Create tables
CREATE TABLE IF NOT EXISTS questions (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    job_title TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    category TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS question_ratings (
    id SERIAL PRIMARY KEY,
    question_id INTEGER REFERENCES questions(id),
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS question_sets (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    job_title TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS question_set_items (
    id SERIAL PRIMARY KEY,
    set_id INTEGER REFERENCES question_sets(id) ON DELETE CASCADE,
    question_id INTEGER REFERENCES questions(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    UNIQUE(set_id, position)
);
EOF

# Copy the init SQL file to the correct location
cp db-scripts/init-database.sql db/init.sql

# Create a temporary docker-compose override file
echo "Creating docker-compose override..."
cat > db-scripts/docker-compose.override.yml << 'EOF'
version: "3.8"

services:
  db:
    environment:
      POSTGRES_DB: interview_prep
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    command: 
      - "postgres"
      - "-c"
      - "log_statement=all"

  backend:
    environment:
      DATABASE_URL: postgresql://postgres:password@db:5432/interview_prep
EOF

# Stop all containers
echo "Stopping all containers..."
docker-compose down

# Remove existing database volume
echo "Removing database volume..."
docker volume rm $(docker volume ls -q | grep postgres_data) 2>/dev/null || echo "No postgres volume to remove."

# Start the database first
echo "Starting database container..."
docker-compose -f docker-compose.yml -f db-scripts/docker-compose.override.yml up -d db

# Wait for database to be ready
echo "Waiting for database to be ready..."
sleep 10

# Start the rest of the services
echo "Starting remaining services..."
docker-compose -f docker-compose.yml -f db-scripts/docker-compose.override.yml up -d

# Display status
echo "Container status:"
docker-compose ps

echo "===== Database Fix Complete ====="
echo "The application should now be available at:"
echo "Frontend: http://ec2-16-16-26-79.eu-north-1.compute.amazonaws.com"
echo "Backend API: http://ec2-16-16-26-79.eu-north-1.compute.amazonaws.com:8000"
echo ""
echo "Check container logs with: docker-compose logs -f"
