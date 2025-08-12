# Build stage
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY src/ui/package*.json ./

# Clear npm cache and install dependencies
RUN npm cache clean --force && \
    npm install --omit=dev

# Copy source code
COPY src/ui/ .

# Force clean build by removing any existing build artifacts
RUN rm -rf build/ && \
    rm -rf node_modules/.cache/ && \
    rm -rf .cache/ && \
    npm run build

# Production stage
FROM nginx:alpine

# Copy built application
COPY --from=builder /app/build /usr/share/nginx/html

# Copy nginx configuration
COPY docker/ui-service/nginx.conf /etc/nginx/nginx.conf

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:80/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
