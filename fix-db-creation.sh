#!/bin/bash
# Fix database creation issue

echo "===== Database Creation Fix ====="
echo "$(date)"

# Make sure Docker is running
if ! systemctl is-active --quiet docker; then
  echo "Docker is not running. Starting Docker..."
  sudo systemctl start docker
fi

# Update .env file to ensure consistent database name
echo "Updating .env file with consistent database name..."
if [ -f .env ]; then
  # Update existing .env file
  sed -i 's/DB_NAME=.*/DB_NAME=interview_prep/g' .env
  echo "Updated DB_NAME in .env file."
else
  # Create new .env file
  cat > .env << 'EOF'
# Database credentials with consistent naming
DB_NAME=interview_prep
DB_USER=postgres
DB_PASSWORD=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=interview_prep

# API key
GEMINI_API_KEY=your-gemini-api-key-here

# Frontend configuration
REACT_APP_API_URL=http://ec2-16-16-26-79.eu-north-1.compute.amazonaws.com:8000
EOF
  echo "Created new .env file with consistent database naming."
fi

# Create a script to create the database
echo "Creating database initialization script..."
mkdir -p db-fix
cat > db-fix/create-db.sql << 'EOF'
-- Create the database if it doesn't exist
CREATE DATABASE interview_prep;
EOF

# Create a script to ensure database is created before the app starts
cat > db-fix/init-db.sh << 'EOF'
#!/bin/bash
set -e

# Wait for postgres to be ready
until PGPASSWORD=$POSTGRES_PASSWORD psql -h "db" -U "postgres" -c '\q'; do
  echo "Postgres is unavailable - sleeping"
  sleep 1
done

echo "Postgres is up - creating database if it doesn't exist"

# Create database if it doesn't exist
PGPASSWORD=$POSTGRES_PASSWORD psql -h "db" -U "postgres" -tc "SELECT 1 FROM pg_database WHERE datname = 'interview_prep'" | grep -q 1 || PGPASSWORD=$POSTGRES_PASSWORD psql -h "db" -U "postgres" -c "CREATE DATABASE interview_prep"

echo "Database setup complete"
EOF

chmod +x db-fix/init-db.sh

# Create a temporary Dockerfile for the backend with database initialization
cat > db-fix/backend-Dockerfile << 'EOF'
FROM python:3.11-slim

# Set environment variables to prevent debconf warnings
ENV DEBIAN_FRONTEND=noninteractive \
    DEBCONF_NOWARNINGS=yes

# System dependencies (curl for healthcheck, postgresql-client for database operations)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    python3-venv \
    postgresql-client \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Set up virtual environment
RUN python -m venv /app/venv

# Make sure we use the virtualenv
ENV PATH="/app/venv/bin:$PATH"
ENV VIRTUAL_ENV="/app/venv"

# Copy and run database initialization script
COPY init-db.sh /app/
RUN chmod +x /app/init-db.sh

# Install Python deps in the virtual environment and create user in a single layer
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install gunicorn uvicorn python-multipart && \
    useradd -m appuser && \
    chown -R appuser:appuser /app

# Copy app code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Expose internal port
EXPOSE 8000

# Run database initialization before starting the app
CMD ["/bin/bash", "-c", "/app/init-db.sh && gunicorn main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 --workers 2 --timeout 60"]
EOF

# Create docker-compose override for consistent database name
echo "Creating docker-compose override..."
cat > db-fix/docker-compose.override.yml << 'EOF'
version: "3.8"

services:
  db:
    environment:
      - POSTGRES_DB=interview_prep
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./db/init.sql:/docker-entrypoint-initdb.d/init.sql
      - ./db-fix/create-db.sql:/docker-entrypoint-initdb.d/01-create-db.sql
  
  backend:
    build:
      context: ./backend
      dockerfile: ../db-fix/backend-Dockerfile
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/interview_prep
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    volumes:
      - ./db-fix/init-db.sh:/app/init-db.sh
EOF

# Stop all containers
echo "Stopping all containers..."
docker-compose down

# Clean up Docker volumes to ensure fresh database
echo "Removing database volume for a clean start..."
docker volume rm $(docker volume ls -q | grep postgres_data) 2>/dev/null || echo "No postgres volume to remove."

# Copy init-db.sh to backend directory
cp db-fix/init-db.sh backend/

# Build and restart with the new configuration
echo "Building and restarting containers..."
docker-compose -f docker-compose.prod.yml -f db-fix/docker-compose.override.yml up -d --build

echo "===== Database Creation Fix Complete ====="
echo "Containers are starting up. Please wait a moment."
echo "You can check the status with: docker-compose logs -f"
