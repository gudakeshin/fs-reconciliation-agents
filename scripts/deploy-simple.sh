#!/bin/bash

# Simple Deployment Script for FS Reconciliation Agents
# Fast deployment without heavy system modifications

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Change to project directory
cd "$(dirname "$0")/.."

log "Starting simple deployment..."

# Check if .env exists
if [[ ! -f ".env" ]]; then
    warning ".env file not found, copying from production.env"
    cp production.env .env
fi

# Stop any running containers
log "Stopping existing containers..."
docker-compose down --remove-orphans 2>/dev/null || true

# Clean up Docker resources
log "Cleaning up Docker resources..."
docker system prune -f

# Build and start services
log "Building and starting services..."
docker-compose up -d --build

# Wait for services to be ready
log "Waiting for services to start..."
sleep 15

# Health checks
log "Performing health checks..."

# Check database
if docker-compose ps database | grep -q "Up"; then
    success "Database is running"
else
    warning "Database may not be ready yet"
fi

# Check Redis
if docker-compose ps redis | grep -q "Up"; then
    success "Redis is running"
else
    warning "Redis may not be ready yet"
fi

# Check API
if curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
    success "API is healthy"
else
    warning "API may not be ready yet"
fi

# Check UI
if curl -f -s http://localhost:3000 > /dev/null 2>&1; then
    success "UI is accessible"
else
    warning "UI may not be ready yet"
fi

# Display service status
echo
log "Service Status:"
docker-compose ps

echo
success "Deployment completed!"
log "Application URLs:"
log "  - UI: http://localhost:3000"
log "  - API: http://localhost:8000"
log "  - Grafana: http://localhost:3001"
log "  - Prometheus: http://localhost:9090"

echo
log "To view logs: docker-compose logs -f"
log "To stop: docker-compose down"
