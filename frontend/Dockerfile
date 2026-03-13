# Stage 1: Build
FROM node:18-alpine AS builder

WORKDIR /app

# Copy dependency manifests first for better layer caching
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci --only=production=false

# Copy source code
COPY frontend/src ./src
COPY frontend/public ./public

# Build the production bundle
RUN npm run build

# Stage 2: Serve with nginx
FROM nginx:alpine

# Copy built assets
COPY --from=builder /app/build /usr/share/nginx/html

# Copy nginx config for SPA routing
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80 || exit 1

CMD ["nginx", "-g", "daemon off;"]
