#!/bin/bash

# FS Reconciliation Agents - Production Deployment Script
# This script deploys the complete application stack

set -e

echo "🚀 FS Reconciliation Agents - Production Deployment"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
check_docker() {
    print_status "Checking Docker availability..."
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    print_status "Docker is running"
}

# Check if Docker Compose is available
check_docker_compose() {
    print_status "Checking Docker Compose availability..."
    if ! docker-compose --version > /dev/null 2>&1; then
        print_error "Docker Compose is not available. Please install Docker Compose and try again."
        exit 1
    fi
    print_status "Docker Compose is available"
}

# Check environment variables
check_environment() {
    print_status "Checking environment variables..."
    
    # Load .env file if it exists
    if [ -f ".env" ]; then
        print_status "Loading environment variables from .env file..."
        export $(cat .env | grep -v '^#' | xargs)
    fi
    
    # Required environment variables
    required_vars=(
        "OPENAI_API_KEY"
        "DATABASE_URL"
        "REDIS_URL"
        "SECRET_KEY"
        "JWT_SECRET_KEY"
    )
    
    missing_vars=()
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        print_error "Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        echo ""
        print_warning "Please set these variables in your environment or .env file"
        exit 1
    fi
    
    print_status "All required environment variables are set"
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    directories=(
        "data"
        "data/uploads"
        "data/reports"
        "logs"
        "logs/nginx"
        "nginx/ssl"
        "monitoring/grafana/dashboards"
        "monitoring/grafana/datasources"
    )
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            print_status "Created directory: $dir"
        fi
    done
}

# Generate SSL certificates (self-signed for development)
generate_ssl_certificates() {
    print_status "Generating SSL certificates..."
    
    if [ ! -f "nginx/ssl/cert.pem" ] || [ ! -f "nginx/ssl/key.pem" ]; then
        print_warning "Generating self-signed SSL certificates for development..."
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout nginx/ssl/key.pem \
            -out nginx/ssl/cert.pem \
            -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
        print_status "SSL certificates generated"
    else
        print_status "SSL certificates already exist"
    fi
}

# Build and start services
deploy_services() {
    print_status "Building and starting services..."
    
    # Stop existing containers
    print_status "Stopping existing containers..."
    docker-compose -f docker-compose.prod.yml down --remove-orphans
    
    # Build images
    print_status "Building Docker images..."
    docker-compose -f docker-compose.prod.yml build --no-cache
    
    # Start services
    print_status "Starting services..."
    docker-compose -f docker-compose.prod.yml up -d
    
    print_status "Services started successfully"
}

# Wait for services to be ready
wait_for_services() {
    print_status "Waiting for services to be ready..."
    
    # Wait for database
    print_status "Waiting for database..."
    timeout=60
    while ! docker-compose -f docker-compose.prod.yml exec -T database pg_isready -U fs_user > /dev/null 2>&1; do
        if [ $timeout -le 0 ]; then
            print_error "Database failed to start within 60 seconds"
            exit 1
        fi
        sleep 1
        timeout=$((timeout - 1))
    done
    print_status "Database is ready"
    
    # Wait for API
    print_status "Waiting for API service..."
    timeout=60
    while ! curl -f http://localhost:8000/health > /dev/null 2>&1; do
        if [ $timeout -le 0 ]; then
            print_error "API service failed to start within 60 seconds"
            exit 1
        fi
        sleep 2
        timeout=$((timeout - 2))
    done
    print_status "API service is ready"
    
    # Wait for UI
    print_status "Waiting for UI service..."
    timeout=60
    while ! curl -f http://localhost:3000 > /dev/null 2>&1; do
        if [ $timeout -le 0 ]; then
            print_error "UI service failed to start within 60 seconds"
            exit 1
        fi
        sleep 2
        timeout=$((timeout - 2))
    done
    print_status "UI service is ready"
}

# Run database migrations
run_migrations() {
    print_status "Running database migrations..."
    
    # Wait a bit more for database to be fully ready
    sleep 5
    
    # Run migrations
    docker-compose -f docker-compose.prod.yml exec -T api-service alembic upgrade head
    
    print_status "Database migrations completed"
}

# Check service health
check_health() {
    print_status "Checking service health..."
    
    # Check API health
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        print_status "✅ API service is healthy"
    else
        print_error "❌ API service is not responding"
        exit 1
    fi
    
    # Check UI health
    if curl -f http://localhost:3000 > /dev/null 2>&1; then
        print_status "✅ UI service is healthy"
    else
        print_error "❌ UI service is not responding"
        exit 1
    fi
    
    # Check database
    if docker-compose -f docker-compose.prod.yml exec -T database pg_isready -U fs_user > /dev/null 2>&1; then
        print_status "✅ Database is healthy"
    else
        print_error "❌ Database is not responding"
        exit 1
    fi
    
    # Check Redis
    if docker-compose -f docker-compose.prod.yml exec -T redis redis-cli ping > /dev/null 2>&1; then
        print_status "✅ Redis is healthy"
    else
        print_error "❌ Redis is not responding"
        exit 1
    fi
}

# Display deployment information
show_deployment_info() {
    echo ""
    echo "🎉 Deployment completed successfully!"
    echo "=================================="
    echo ""
    echo "Services:"
    echo "  🌐 Application: http://localhost"
    echo "  📊 API Documentation: http://localhost/docs"
    echo "  📈 Grafana Dashboard: http://localhost:3001"
    echo "  📊 Prometheus: http://localhost:9090"
    echo ""
    echo "Default credentials:"
    echo "  Grafana: admin / admin"
    echo ""
    echo "To view logs:"
    echo "  docker-compose -f docker-compose.prod.yml logs -f"
    echo ""
    echo "To stop services:"
    echo "  docker-compose -f docker-compose.prod.yml down"
    echo ""
}

# Main deployment function
main() {
    check_docker
    check_docker_compose
    check_environment
    create_directories
    generate_ssl_certificates
    deploy_services
    wait_for_services
    run_migrations
    check_health
    show_deployment_info
}

# Run main function
main "$@" 