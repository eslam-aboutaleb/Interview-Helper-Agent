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

# Create JSX IntrinsicElements type definition
RUN mkdir -p /app/src && \
    echo '// This file contains custom TypeScript declarations for JSX elements\n\
declare namespace JSX {\n\
  interface IntrinsicElements {\n\
    div: any;\n\
    main: any;\n\
    nav: any;\n\
    header: any;\n\
    a: any;\n\
    button: any;\n\
    span: any;\n\
    h1: any;\n\
    h2: any;\n\
    h3: any;\n\
    h4: any;\n\
    h5: any;\n\
    h6: any;\n\
    p: any;\n\
    form: any;\n\
    input: any;\n\
    textarea: any;\n\
    select: any;\n\
    option: any;\n\
    label: any;\n\
    ul: any;\n\
    ol: any;\n\
    li: any;\n\
    table: any;\n\
    tr: any;\n\
    td: any;\n\
    th: any;\n\
    section: any;\n\
    img: any;\n\
    svg: any;\n\
    path: any;\n\
    [elemName: string]: any;\n\
  }\n\
}\n\
\n\
declare module \"react/jsx-runtime\";\n\
declare module \"react/jsx-dev-runtime\";\n\
declare module \"react-hot-toast\";\n' > /app/src/jsx.d.ts

# Install dependencies and TypeScript type definitions with exact versions
RUN npm ci --no-fund --no-audit --prefer-offline --silent && \
    npm install --save-dev @types/react@18.2.45 @types/react-dom@18.2.17 @types/react-router-dom@5.3.3 typescript && \
    # Create tsconfig with jsx runtime settings
    echo '{\n\
  "compilerOptions": {\n\
    "target": "es5",\n\
    "lib": ["dom", "dom.iterable", "esnext"],\n\
    "allowJs": true,\n\
    "skipLibCheck": true,\n\
    "esModuleInterop": true,\n\
    "allowSyntheticDefaultImports": true,\n\
    "strict": false,\n\
    "forceConsistentCasingInFileNames": true,\n\
    "noFallthroughCasesInSwitch": true,\n\
    "module": "esnext",\n\
    "moduleResolution": "node",\n\
    "resolveJsonModule": true,\n\
    "isolatedModules": true,\n\
    "noEmit": true,\n\
    "jsx": "react-jsx",\n\
    "jsxImportSource": "react"\n\
  },\n\
  "include": ["src"]\n\
}' > ./tsconfig.json

# Copy the rest of the frontend source code
COPY ./src ./src
COPY ./public ./public
COPY ./postcss.config.js ./
COPY ./tailwind.config.js ./

# Build the React app with production optimizations
RUN DISABLE_ESLINT_PLUGIN=true npm run build

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
