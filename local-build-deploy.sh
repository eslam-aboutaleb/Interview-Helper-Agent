#!/bin/bash

# Script to pre-build frontend locally and prepare for EC2 deployment

echo "===== Starting local frontend build process ====="
echo "This will build your frontend locally, which is faster than building on EC2"

# Set the EC2 instance details
read -p "Enter your EC2 instance public DNS or IP: " EC2_HOST
read -p "Enter your EC2 username (e.g., ubuntu): " EC2_USER
read -p "Enter path to your SSH key file: " SSH_KEY

# Ensure we have the required inputs
if [ -z "$EC2_HOST" ] || [ -z "$EC2_USER" ] || [ -z "$SSH_KEY" ]; then
  echo "Error: Missing required parameters"
  exit 1
fi

# Check if SSH key file exists
if [ ! -f "$SSH_KEY" ]; then
  echo "Error: SSH key file not found at $SSH_KEY"
  exit 1
fi

# Create a temporary directory for the build
TEMP_DIR=$(mktemp -d)
echo "Creating temporary build directory: $TEMP_DIR"

# Build frontend locally (this is faster than on EC2)
echo "===== Building frontend locally ====="
cd frontend

# Ensure we have the latest dependencies
npm ci

# Build with production settings
echo "Running build process..."
GENERATE_SOURCEMAP=false CI=true npm run build

if [ $? -ne 0 ]; then
  echo "Frontend build failed!"
  exit 1
fi

echo "Local build completed successfully!"

# Prepare the build for transfer
echo "===== Preparing build for transfer ====="
cp -r build/* $TEMP_DIR/
cd ..

# Create a tar archive
echo "Creating archive of built files..."
tar -czf frontend-build.tar.gz -C $TEMP_DIR .

# Clean up temporary directory
rm -rf $TEMP_DIR

# Transfer to EC2
echo "===== Transferring build to EC2 ====="
scp -i "$SSH_KEY" frontend-build.tar.gz $EC2_USER@$EC2_HOST:~/

# Set up on EC2
echo "===== Setting up on EC2 ====="
ssh -i "$SSH_KEY" $EC2_USER@$EC2_HOST <<'EOF'
  cd ~/project
  mkdir -p frontend/build
  tar -xzf ~/frontend-build.tar.gz -C frontend/build/
  
  # Update docker-compose to use the pre-built files
  cat > frontend/Dockerfile.prebuilt <<'DOCKERFILE'
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
  echo "Now run: ./ec2-deploy.sh --prebuilt"
EOF

# Clean up local archive
rm frontend-build.tar.gz

echo "===== Local build and transfer complete ====="
echo "Connect to your EC2 instance and run: ./ec2-deploy.sh --prebuilt"
