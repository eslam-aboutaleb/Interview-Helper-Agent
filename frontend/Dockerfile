FROM node:18-alpine as build

WORKDIR /app

# Set environment variables for optimized builds
ENV CI=true
ENV NODE_ENV=production 
ENV GENERATE_SOURCEMAP=false
# Increase Node memory limit - using 4GB instead of 2GB
ENV NODE_OPTIONS="--max-old-space-size=4096"

# Copy package.json and package-lock.json first for better layer caching
COPY package*.json ./

# Install dependencies and TypeScript type definitions with exact versions
RUN npm ci --no-fund --no-audit --prefer-offline --silent && \
    npm install --save-dev @types/react@18.2.45 @types/react-dom@18.2.17 && \
    # Create tsconfig with jsx runtime settings
    echo '{ "compilerOptions": { "jsx": "react-jsx", "esModuleInterop": true, "skipLibCheck": true } }' > ./tsconfig.temp.json && \
    cat ./tsconfig.temp.json

# Copy the rest of the frontend source code
COPY ./src ./src
COPY ./public ./public
COPY ./tsconfig.json ./
COPY ./postcss.config.js ./
COPY ./tailwind.config.js ./

# Build the React app with production optimizations
RUN npm run build

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
