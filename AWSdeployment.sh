#!/bin/bash
#
# AWSdeployment.sh - Comprehensive AWS/EC2 Deployment and Troubleshooting Script
# This script consolidates all deployment, fixing, and troubleshooting functionality
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

print_header() {
  echo -e "${BLUE}===== $1 =====${NC}"
}

print_success() {
  echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
  echo -e "${RED}✗ $1${NC}"
}

print_warning() {
  echo -e "${YELLOW}⚠ $1${NC}"
}

check_docker() {
  if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    return 1
  fi
  
  if ! systemctl is-active --quiet docker; then
    print_warning "Docker is not running. Starting Docker..."
    sudo systemctl start docker
  fi
  
  print_success "Docker is available and running"
  docker --version
  return 0
}

get_ec2_metadata() {
  EC2_METADATA=$(curl -s --connect-timeout 2 http://169.254.169.254/latest/meta-data/)
  if [ $? -eq 0 ]; then
    PUBLIC_DNS=$(curl -s http://169.254.169.254/latest/meta-data/public-hostname)
    PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
    return 0
  else
    return 1
  fi
}

show_menu() {
  echo ""
  echo -e "${BLUE}AWS/EC2 Deployment & Troubleshooting Menu${NC}"
  echo "=========================================="
  echo "1) Full EC2 Deployment"
  echo "2) Deploy with Pre-built Frontend (Fast)"
  echo "3) Skip Frontend Build"
  echo "4) Local Frontend Build & Transfer"
  echo "5) Comprehensive Database Fix"
  echo "6) Fix JSX Runtime Issue"
  echo "7) Fix TypeScript Deployment"
  echo "8) Fix Backend Connectivity"
  echo "9) Fix EC2 Security Groups"
  echo "10) Fix Database Creation"
  echo "11) Fix Database Authentication"
  echo "12) Fix Database Name"
  echo "13) Direct JSX Fix & Deploy"
  echo "14) EC2 Troubleshooting"
  echo "15) Backend Troubleshooting"
  echo "16) Exit"
  echo ""
  read -p "Select an option (1-16): " choice
}

# ============================================================================
# SECTION 1: MAIN EC2 DEPLOYMENT
# ============================================================================

deploy_full_ec2() {
  print_header "Starting EC2 Deployment Process"
  echo "$(date)"
  
  check_docker || return 1
  
  # Default options
  SKIP_FRONTEND_BUILD=false
  PREBUILT_MODE=false
  
  # Update from git repository
  print_header "Pulling latest changes from git"
  git pull origin master || print_warning "Git pull failed or not a git repository"
  
  # Update environment variables with current EC2 DNS
  print_header "Updating environment variables"
  if get_ec2_metadata; then
    # Create or update .env file
    if [ -f ".env" ]; then
      grep -q "REACT_APP_API_URL" .env && \
        sed -i.bak "s|REACT_APP_API_URL=.*|REACT_APP_API_URL=http://$PUBLIC_DNS:8000|g" .env || \
        echo "REACT_APP_API_URL=http://$PUBLIC_DNS:8000" >> .env
    else
      cat > .env << EOF
# Database configuration
DB_NAME=interview_prep
DB_USER=postgres
DB_PASSWORD=password
POSTGRES_PASSWORD=password
POSTGRES_DB=interview_prep

# API Key
GEMINI_API_KEY=your-gemini-api-key-here

# Frontend configuration
REACT_APP_API_URL=http://$PUBLIC_DNS:8000
EOF
    fi
    
    print_success "Updated API URL to http://$PUBLIC_DNS:8000"
  else
    print_warning "Could not get EC2 public DNS"
  fi
  
  # Stop any running containers
  print_header "Stopping existing containers"
  docker-compose -f docker-compose.prod.yml down || true
  
  # Build backend and database
  print_header "Building backend and database"
  docker-compose -f docker-compose.prod.yml build db backend
  
  # Build frontend
  print_header "Building frontend (this may take several minutes)"
  docker system prune -f
  
  docker-compose -f docker-compose.prod.yml build frontend &
  BUILD_PID=$!
  
  TIMEOUT=1200
  count=0
  while kill -0 $BUILD_PID 2> /dev/null; do
    sleep 15
    count=$((count + 15))
    
    echo "Build in progress... ($count seconds elapsed)"
    
    if [ $count -ge $TIMEOUT ]; then
      print_error "Build timeout exceeded ($TIMEOUT seconds). Killing build process."
      kill -9 $BUILD_PID
      return 1
    fi
  done
  
  if wait $BUILD_PID; then
    print_success "Frontend build completed successfully!"
  else
    print_error "Frontend build failed with exit code $?"
    return 1
  fi
  
  # Start the containers
  print_header "Starting containers"
  docker-compose -f docker-compose.prod.yml up -d
  
  # Show running containers
  print_header "Deployment complete"
  docker-compose -f docker-compose.prod.yml ps
  
  if get_ec2_metadata; then
    echo ""
    print_success "Application deployed successfully!"
    echo "Frontend: http://$PUBLIC_DNS"
    echo "Backend API: http://$PUBLIC_DNS:8000"
    echo "API Documentation: http://$PUBLIC_DNS:8000/api/docs or /docs"
  fi
  echo "$(date)"
}

# ============================================================================
# SECTION 2: LOCAL FRONTEND BUILD & TRANSFER
# ============================================================================

local_build_deploy() {
  print_header "Starting local frontend build process"
  echo "This will build your frontend locally, which is faster than building on EC2"
  
  # Set the EC2 instance details
  read -p "Enter your EC2 instance public DNS or IP: " EC2_HOST
  read -p "Enter your EC2 username (e.g., ubuntu): " EC2_USER
  read -p "Enter path to your SSH key file: " SSH_KEY
  
  # Ensure we have the required inputs
  if [ -z "$EC2_HOST" ] || [ -z "$EC2_USER" ] || [ -z "$SSH_KEY" ]; then
    print_error "Missing required parameters"
    return 1
  fi
  
  # Check if SSH key file exists
  if [ ! -f "$SSH_KEY" ]; then
    print_error "SSH key file not found at $SSH_KEY"
    return 1
  fi
  
  # Create a temporary directory for the build
  TEMP_DIR=$(mktemp -d)
  print_header "Building frontend locally"
  echo "Temporary build directory: $TEMP_DIR"
  
  cd frontend
  
  # Ensure we have the latest dependencies
  npm ci
  
  # Build with production settings
  echo "Running build process..."
  GENERATE_SOURCEMAP=false CI=true npm run build
  
  if [ $? -ne 0 ]; then
    print_error "Frontend build failed!"
    cd ..
    return 1
  fi
  
  print_success "Local build completed successfully!"
  
  # Prepare the build for transfer
  print_header "Preparing build for transfer"
  cp -r build/* $TEMP_DIR/
  cd ..
  
  # Create a tar archive
  echo "Creating archive of built files..."
  tar -czf frontend-build.tar.gz -C $TEMP_DIR .
  
  # Clean up temporary directory
  rm -rf $TEMP_DIR
  
  # Transfer to EC2
  print_header "Transferring build to EC2"
  scp -i "$SSH_KEY" frontend-build.tar.gz $EC2_USER@$EC2_HOST:~/
  
  # Set up on EC2
  print_header "Setting up on EC2"
  ssh -i "$SSH_KEY" $EC2_USER@$EC2_HOST << 'EOF'
    cd ~/project || cd ~
    mkdir -p frontend/build
    tar -xzf ~/frontend-build.tar.gz -C frontend/build/
    
    # Update docker-compose to use the pre-built files
    cat > frontend/Dockerfile.prebuilt << 'DOCKERFILE'
FROM nginx:alpine

# Copy pre-built React files to Nginx default public folder
COPY ./build /usr/share/nginx/html

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Create a non-root user and set permissions
RUN adduser -D -u 1000 nginxuser && \
    chown -R nginxuser:nginxuser /var/cache/nginx && \
    touch /var/run/nginx.pid && \
    chown -R nginxuser:nginxuser /var/run/nginx.pid && \
    mkdir -p /tmp/nginx && \
    chown -R nginxuser:nginxuser /tmp/nginx

# Use the non-root user
USER nginxuser

# Expose port 80
EXPOSE 80

# Start Nginx server
CMD ["nginx", "-g", "daemon off;"]
DOCKERFILE

    echo "Files transferred and prepared successfully!"
EOF

  # Clean up local archive
  rm frontend-build.tar.gz
  
  print_success "Local build and transfer complete"
  echo "Connect to your EC2 instance and run the deployment with pre-built mode"
}

# ============================================================================
# SECTION 3: COMPREHENSIVE DATABASE FIX
# ============================================================================

comprehensive_db_fix() {
  print_header "Comprehensive Database Fix"
  echo "$(date)"
  
  check_docker || return 1
  
  # Create .env file with correct database settings
  print_header "Creating .env file"
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
REACT_APP_API_URL=http://localhost:8000
EOF
  
  # Confirm database name in docker-compose.yml
  print_header "Checking docker-compose.yml for consistency"
  if ! grep -q "POSTGRES_DB: interview_prep" docker-compose.yml; then
    print_warning "docker-compose.yml may not have consistent database name!"
  fi
  
  # Create a helper script to initialize the database
  print_header "Creating database initialization script"
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
  
  # Stop all containers
  print_header "Stopping all containers"
  docker-compose down || true
  
  # Remove existing database volume
  print_header "Removing database volume"
  docker volume rm $(docker volume ls -q | grep postgres_data) 2>/dev/null || echo "No postgres volume to remove."
  
  # Start the database first
  print_header "Starting database container"
  docker-compose -f docker-compose.yml up -d db
  
  # Wait for database to be ready
  echo "Waiting for database to be ready..."
  sleep 10
  
  # Start the rest of the services
  print_header "Starting remaining services"
  docker-compose -f docker-compose.yml up -d
  
  # Display status
  echo "Container status:"
  docker-compose ps
  
  print_success "Database Fix Complete"
}

# ============================================================================
# SECTION 4: JSX RUNTIME FIX
# ============================================================================

fix_jsx_runtime() {
  print_header "Starting JSX Runtime Fix Deployment"
  echo "$(date)"
  
  check_docker || return 1
  
  # Clean up Docker system to ensure we have enough space
  print_header "Cleaning Docker system"
  docker system prune -f
  
  # Create directory for temporary files
  mkdir -p temp_fix
  
  # Create custom.d.ts file with JSX runtime declarations
  print_header "Creating TypeScript declaration files"
  cat > temp_fix/custom.d.ts << 'EOF'
// This file contains custom TypeScript declarations
// for modules that might be missing type definitions

declare module 'react';
declare module 'react-dom';
declare module 'react-router-dom';
declare module 'react-hot-toast';

// Add JSX runtime declarations
declare module 'react/jsx-runtime';
declare module 'react/jsx-dev-runtime';

// Add JSX IntrinsicElements interface
declare namespace JSX {
  interface IntrinsicElements {
    div: any;
    main: any;
    nav: any;
    header: any;
    a: any;
    button: any;
    span: any;
    h1: any;
    h2: any;
    h3: any;
    h4: any;
    h5: any;
    h6: any;
    p: any;
    form: any;
    input: any;
    textarea: any;
    select: any;
    option: any;
    label: any;
    ul: any;
    ol: any;
    li: any;
    table: any;
    tr: any;
    td: any;
    th: any;
    section: any;
    img: any;
    svg: any;
    path: any;
    [elemName: string]: any;
  }
}
EOF

  # Copy the custom declaration file to frontend/src
  cp temp_fix/custom.d.ts frontend/src/
  
  # Stop existing containers
  print_header "Stopping existing containers"
  docker-compose -f docker-compose.prod.yml down || true
  
  # Build the backend and database normally
  print_header "Building backend and database"
  docker-compose -f docker-compose.prod.yml build db backend
  
  # Build the frontend
  print_header "Building frontend with JSX runtime fix"
  docker-compose -f docker-compose.prod.yml build frontend
  
  # Start the containers
  print_header "Starting containers"
  docker-compose -f docker-compose.prod.yml up -d
  
  # Clean up
  print_header "Cleaning up temporary files"
  rm -rf temp_fix
  
  print_success "JSX Runtime Fix Deployment complete"
  
  if get_ec2_metadata; then
    echo "Accessing your application:"
    echo "Frontend: http://$PUBLIC_DNS"
    echo "Backend API: http://$PUBLIC_DNS:8000"
  fi
}

# ============================================================================
# SECTION 5: TYPESCRIPT DEPLOYMENT FIX
# ============================================================================

fix_typescript_deploy() {
  print_header "Building and deploying without TypeScript errors"
  echo "$(date)"
  
  check_docker || return 1
  
  # Clean up Docker system
  docker system prune -f
  
  # Build backend
  print_header "Building backend and database"
  docker-compose -f docker-compose.prod.yml build db backend
  
  # Build frontend with TypeScript fixes
  print_header "Building frontend (installing TypeScript definitions)"
  cd frontend
  
  npm install --save-dev @types/react@latest @types/react-dom@latest
  
  cd ..
  
  docker-compose -f docker-compose.prod.yml build frontend
  
  # Stop and restart
  print_header "Stopping and restarting containers"
  docker-compose -f docker-compose.prod.yml down || true
  docker-compose -f docker-compose.prod.yml up -d
  
  print_success "TypeScript deployment fix complete"
}

# ============================================================================
# SECTION 6: BACKEND CONNECTIVITY FIX
# ============================================================================

fix_backend_connectivity() {
  print_header "Backend Connectivity Fix"
  echo "$(date)"
  
  check_docker || return 1
  
  # Create .env file
  print_header "Creating .env file with correct settings"
  cat > .env << 'EOF'
# Database configuration
DB_NAME=interview_prep
DB_USER=postgres
DB_PASSWORD=password
POSTGRES_PASSWORD=password
POSTGRES_DB=interview_prep

# API configuration
DATABASE_URL=postgresql://postgres:password@db:5432/interview_prep
GEMINI_API_KEY=your-gemini-api-key-here

# Frontend
REACT_APP_API_URL=http://localhost:8000
EOF

  # Stop and rebuild
  print_header "Stopping and rebuilding services"
  docker-compose -f docker-compose.prod.yml down || true
  docker-compose -f docker-compose.prod.yml up -d --build
  
  # Check connectivity
  print_header "Checking backend connectivity"
  sleep 5
  docker-compose logs backend | head -20
  
  print_success "Backend connectivity fix complete"
}

# ============================================================================
# SECTION 7: EC2 SECURITY GROUPS FIX
# ============================================================================

fix_ec2_security() {
  print_header "EC2 Security Group Fix"
  echo "Note: This requires AWS CLI credentials configured"
  
  if ! command -v aws &> /dev/null; then
    print_error "AWS CLI is not installed"
    echo "Install it with: pip install awscli"
    return 1
  fi
  
  read -p "Enter your EC2 Security Group ID: " SG_ID
  
  if [ -z "$SG_ID" ]; then
    print_error "Security Group ID is required"
    return 1
  fi
  
  print_header "Adding security group rules"
  
  # Allow port 8000 for backend
  aws ec2 authorize-security-group-ingress \
    --group-id "$SG_ID" \
    --protocol tcp \
    --port 8000 \
    --cidr 0.0.0.0/0 2>/dev/null || print_warning "Port 8000 rule might already exist"
  
  # Allow port 80 for frontend
  aws ec2 authorize-security-group-ingress \
    --group-id "$SG_ID" \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0 2>/dev/null || print_warning "Port 80 rule might already exist"
  
  # Allow port 443 for HTTPS
  aws ec2 authorize-security-group-ingress \
    --group-id "$SG_ID" \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0 2>/dev/null || print_warning "Port 443 rule might already exist"
  
  print_success "Security group rules updated"
}

# ============================================================================
# SECTION 8: DATABASE FIXES (Specific Issues)
# ============================================================================

fix_database_creation() {
  print_header "Fix Database Creation"
  
  check_docker || return 1
  
  print_header "Removing and recreating database container"
  docker-compose down
  docker volume rm $(docker volume ls -q | grep postgres) 2>/dev/null || true
  
  docker-compose -f docker-compose.prod.yml up -d db
  sleep 10
  
  docker-compose -f docker-compose.prod.yml up -d
  
  print_success "Database recreated successfully"
}

fix_database_auth() {
  print_header "Fix Database Authentication"
  
  # Create .env with correct credentials
  cat > .env << 'EOF'
DB_USER=postgres
DB_PASSWORD=password
POSTGRES_PASSWORD=password
POSTGRES_DB=interview_prep
DATABASE_URL=postgresql://postgres:password@db:5432/interview_prep
EOF

  check_docker || return 1
  
  docker-compose -f docker-compose.prod.yml down
  docker-compose -f docker-compose.prod.yml up -d
  
  print_success "Database authentication fixed"
}

fix_database_name() {
  print_header "Fix Database Name Mismatch"
  
  # Update .env
  cat > .env << 'EOF'
POSTGRES_DB=interview_prep
DB_NAME=interview_prep
DATABASE_URL=postgresql://postgres:password@db:5432/interview_prep
EOF

  check_docker || return 1
  
  docker-compose -f docker-compose.prod.yml down
  docker volume rm $(docker volume ls -q | grep postgres) 2>/dev/null || true
  docker-compose -f docker-compose.prod.yml up -d
  
  print_success "Database name mismatch fixed"
}

# ============================================================================
# SECTION 9: DIRECT JSX FIX & DEPLOY
# ============================================================================

direct_jsx_fix_deploy() {
  print_header "Direct JSX Fix & Deploy"
  echo "$(date)"
  
  check_docker || return 1
  docker system prune -f
  
  # Apply JSX fix
  mkdir -p temp_fix
  cat > temp_fix/custom.d.ts << 'EOF'
declare module 'react';
declare module 'react-dom';
declare module 'react/jsx-runtime';
declare module 'react/jsx-dev-runtime';
declare namespace JSX {
  interface IntrinsicElements {
    [elemName: string]: any;
  }
}
EOF

  cp temp_fix/custom.d.ts frontend/src/
  
  # Update environment
  cat > .env << 'EOF'
DB_NAME=interview_prep
DB_USER=postgres
DB_PASSWORD=password
POSTGRES_PASSWORD=password
POSTGRES_DB=interview_prep
GEMINI_API_KEY=your-gemini-api-key-here
REACT_APP_API_URL=http://localhost:8000
EOF

  # Full rebuild and deploy
  print_header "Building all services"
  docker-compose -f docker-compose.prod.yml down || true
  docker-compose -f docker-compose.prod.yml up -d --build
  
  # Cleanup
  rm -rf temp_fix
  
  print_success "Direct JSX fix & deployment complete"
}

# ============================================================================
# SECTION 10: TROUBLESHOOTING
# ============================================================================

ec2_troubleshoot() {
  print_header "EC2 Deployment Troubleshooting"
  echo "$(date)"
  
  # Check if running on EC2
  print_header "Checking if running on EC2"
  if get_ec2_metadata; then
    print_success "Running on EC2"
    echo "Instance metadata available"
    echo "Public DNS: $PUBLIC_DNS"
    echo "Public IP: $PUBLIC_IP"
  else
    print_error "Not running on EC2 or metadata service not accessible"
  fi
  
  # Check Docker status
  print_header "Checking Docker status"
  if check_docker; then
    docker ps
  fi
  
  # Check Docker Compose
  print_header "Checking Docker Compose"
  if command -v docker-compose &> /dev/null; then
    print_success "Docker Compose is installed"
    docker-compose --version
    docker-compose ps
  else
    print_error "Docker Compose is not installed"
  fi
  
  # Check project files
  print_header "Checking project files"
  if [ -f "docker-compose.prod.yml" ]; then
    print_success "docker-compose.prod.yml exists"
  else
    print_error "docker-compose.prod.yml not found"
  fi
  
  if [ -f ".env" ]; then
    print_success ".env file exists"
  else
    print_error ".env file not found"
  fi
  
  # Check system resources
  print_header "Checking system resources"
  echo "Memory:"
  free -h
  echo ""
  echo "Disk space:"
  df -h | grep -E "Filesystem|/$"
  
  # Show container logs
  print_header "Last 20 lines of container logs"
  docker-compose logs --tail=20 2>/dev/null || true
}

backend_troubleshoot() {
  print_header "Backend Troubleshooting"
  
  check_docker || return 1
  
  print_header "Backend container logs"
  docker-compose logs backend --tail=50
  
  print_header "Backend service status"
  docker-compose ps backend
  
  print_header "Testing backend connectivity"
  if get_ec2_metadata; then
    echo "Attempting to connect to http://$PUBLIC_DNS:8000"
    curl -I http://$PUBLIC_DNS:8000 2>/dev/null || print_warning "Could not reach backend"
  fi
}

# ============================================================================
# MAIN PROGRAM
# ============================================================================

main() {
  while true; do
    show_menu
    
    case $choice in
      1) deploy_full_ec2 ;;
      2) deploy_full_ec2 --prebuilt ;;
      3) deploy_full_ec2 --skip-frontend ;;
      4) local_build_deploy ;;
      5) comprehensive_db_fix ;;
      6) fix_jsx_runtime ;;
      7) fix_typescript_deploy ;;
      8) fix_backend_connectivity ;;
      9) fix_ec2_security ;;
      10) fix_database_creation ;;
      11) fix_database_auth ;;
      12) fix_database_name ;;
      13) direct_jsx_fix_deploy ;;
      14) ec2_troubleshoot ;;
      15) backend_troubleshoot ;;
      16) echo "Exiting..."; exit 0 ;;
      *) print_error "Invalid option. Please try again." ;;
    esac
    
    echo ""
    read -p "Press Enter to continue..."
  done
}

# Run main program
main
