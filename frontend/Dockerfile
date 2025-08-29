FROM node:18-alpine as build

WORKDIR /app

# Copy package.json and package-lock.json first for better layer caching
COPY package*.json ./

# Install dependencies with specific flags to prevent hanging
# --no-fund to avoid funding messages
# --loglevel=verbose for detailed logs
# CI=true to run in CI mode which prevents interactive prompts
ENV CI=true
RUN npm install --no-fund --loglevel=verbose --no-audit

# Copy the rest of the frontend source code
COPY ./src ./src
COPY ./public ./public
COPY ./tsconfig.json ./
COPY ./postcss.config.js ./
COPY ./tailwind.config.js ./

# Build the React app with increased memory limit and production flag
ENV NODE_OPTIONS="--max-old-space-size=2048"
RUN npm run build --production

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
