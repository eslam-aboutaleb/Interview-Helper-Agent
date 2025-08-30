#!/bin/bash
# Quick fix for database name mismatch

echo "===== Quick Database Name Fix ====="

# Update .env file to match docker-compose.yml
echo "Creating consistent .env file..."
cat > .env << 'EOF'
# Database settings
DB_NAME=interview_prep
DB_USER=postgres
DB_PASSWORD=password
POSTGRES_PASSWORD=password
POSTGRES_DB=interview_prep

# API key 
GEMINI_API_KEY=your-gemini-api-key-here

# Frontend configuration
REACT_APP_API_URL=http://ec2-16-16-26-79.eu-north-1.compute.amazonaws.com:8000
EOF

# Stop containers
echo "Stopping containers..."
docker-compose down

# Remove database volume
echo "Removing database volume..."
docker volume rm $(docker volume ls -q | grep postgres_data) 2>/dev/null || echo "No postgres volume to remove."

# Create directory for database initialization
mkdir -p db/init.sql

# Create database initialization SQL
echo "Creating database initialization script..."
cat > db/init.sql/01-create-db.sql << 'EOF'
-- This script initializes the database

-- Create the interview_prep database if it doesn't exist
CREATE DATABASE interview_prep WITH OWNER postgres;

-- Connect to the interview_prep database to create tables
\c interview_prep

-- Create tables
CREATE TABLE IF NOT EXISTS questions (
    id SERIAL PRIMARY KEY,
    job_title VARCHAR(255) NOT NULL,
    question_text TEXT NOT NULL,
    question_type VARCHAR(50) NOT NULL, -- 'technical' or 'behavioral'
    difficulty INTEGER DEFAULT 1,       -- 1-5 scale
    is_flagged BOOLEAN DEFAULT FALSE,
    tags VARCHAR(500),                  -- Comma-separated tags
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS question_sets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    job_title VARCHAR(255) NOT NULL,
    question_ids TEXT,                  -- JSON array of question IDs
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS user_ratings (
    id SERIAL PRIMARY KEY,
    question_id INTEGER NOT NULL,
    rating DECIMAL(2,1) NOT NULL,       -- 1.0-5.0 scale
    feedback TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
EOF

# Use the standard docker-compose.yml file
echo "Building and starting containers..."
docker-compose up -d --build

echo "===== Fix Complete ====="
echo "Wait a few moments for the containers to start."
echo "To check logs, run: docker-compose logs -f"
echo "Access your application at:"
echo "Frontend: http://ec2-16-16-26-79.eu-north-1.compute.amazonaws.com"
echo "Backend API: http://ec2-16-16-26-79.eu-north-1.compute.amazonaws.com:8000"
