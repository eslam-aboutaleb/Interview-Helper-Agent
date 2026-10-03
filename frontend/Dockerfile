# Stage 1: Build the Vite app
FROM node:20-alpine AS build

WORKDIR /app

# Copy dependency manifests first for better layer caching
COPY package.json package-lock.json ./

# Install dependencies (esbuild's platform binary ships as a
# regular @esbuild/* dependency, so no postinstall network access is needed)
RUN npm ci --no-fund --no-audit

# Copy the rest of the frontend source and build config
COPY . .

# Type-check and build for production (outputs to dist/)
RUN npm run build

# Stage 2: Serve the static bundle with Nginx
FROM nginx:alpine

# Copy built assets from the build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom nginx config (serves SPA + proxies /api to the backend)
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
