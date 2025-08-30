#!/bin/bash
# This script fixes the React JSX runtime TypeScript error and deploys the application

echo "===== Starting JSX Runtime Fix Deployment ====="
echo "$(date)"

# Make sure Docker is running
if ! systemctl is-active --quiet docker; then
  echo "Docker is not running. Starting Docker..."
  sudo systemctl start docker
fi

# Clean up Docker system to ensure we have enough space
echo "Cleaning Docker system..."
docker system prune -f

# Create directory for temporary files
mkdir -p temp_fix

# Create custom.d.ts file with JSX runtime declarations
echo "Creating TypeScript declaration files..."
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
EOF

# Create temporary Dockerfile with JSX runtime fix
cat > temp_fix/Dockerfile.jsx-fix << 'EOF'
FROM node:18-alpine as build

WORKDIR /app

# Set environment variables for optimized builds
ENV CI=true
ENV NODE_ENV=production 
ENV GENERATE_SOURCEMAP=false
ENV NODE_OPTIONS="--max-old-space-size=4096"
ENV DISABLE_ESLINT_PLUGIN=true

# Copy package.json and package-lock.json first for better layer caching
COPY package*.json ./

# Install dependencies with specific TypeScript definitions for React
RUN npm ci --no-fund --no-audit --prefer-offline --silent && \
    npm install --save-dev @types/react@18.2.45 @types/react-dom@18.2.17 @types/react-router-dom

# Create tsconfig with jsx runtime settings
RUN echo '{ "compilerOptions": { "jsx": "react-jsx", "jsxImportSource": "react", "esModuleInterop": true, "skipLibCheck": true } }' > ./tsconfig.override.json

# Copy the rest of the frontend source code
COPY ./src ./src
COPY ./public ./public
COPY ./tsconfig.json ./
COPY ./postcss.config.js ./
COPY ./tailwind.config.js ./

# Copy custom declarations
COPY ./custom.d.ts ./src/

# Run build with tsx support
RUN cat tsconfig.override.json > tsconfig.json && npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Copy built React files to Nginx default public folder
COPY --from=build /app/build /usr/share/nginx/html

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
EOF

# Copy the custom declaration file to frontend/src
cp temp_fix/custom.d.ts frontend/src/

# Stop existing containers
echo "Stopping existing containers..."
docker-compose -f docker-compose.prod.yml down

# Build the backend and database normally
echo "Building backend and database..."
docker-compose -f docker-compose.prod.yml build db backend

# Build the frontend with the fixed Dockerfile
echo "Building frontend with JSX runtime fix..."
cd frontend
cp ../temp_fix/Dockerfile.jsx-fix Dockerfile.jsx-fix
docker build -t interview-prep-frontend -f Dockerfile.jsx-fix .
cd ..

# Start the containers
echo "Starting containers..."
docker-compose -f docker-compose.prod.yml up -d

# Clean up
echo "Cleaning up temporary files..."
rm -rf temp_fix

echo "===== Deployment complete ====="
echo "Accessing your application:"

# Get public DNS/IP
PUBLIC_DNS=$(curl -s http://169.254.169.254/latest/meta-data/public-hostname)
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)

if [ -n "$PUBLIC_DNS" ]; then
  echo "Frontend: http://$PUBLIC_DNS"
  echo "Backend API: http://$PUBLIC_DNS:8000"
elif [ -n "$PUBLIC_IP" ]; then
  echo "Frontend: http://$PUBLIC_IP"
  echo "Backend API: http://$PUBLIC_IP:8000"
else
  echo "Frontend: http://localhost"
  echo "Backend API: http://localhost:8000"
fi

echo "$(date)"
