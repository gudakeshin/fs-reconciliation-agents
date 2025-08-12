#!/bin/bash

# FS Reconciliation Agents - Production Deployment Script
# This script handles secure deployment to production environment

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"
BACKUP_DIR="/var/backups/fs-reconciliation"
LOG_FILE="/var/log/fs-reconciliation/deployment.log"

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root for security reasons"
    fi
}

# Validate environment file
validate_environment() {
    log "Validating production environment configuration..."
    
    if [[ ! -f "$ENV_FILE" ]]; then
        error "Production environment file not found: $ENV_FILE"
    fi
    
    # Check for placeholder values (only warn in development)
    if grep -q "your-super-secure-secret-key-change-this-in-production" "$ENV_FILE"; then
        warning "Using default SECRET_KEY - update for production"
    fi
    
    if grep -q "your-production-openai-api-key" "$ENV_FILE"; then
        warning "Using default OPENAI_API_KEY - update for production"
    fi
    
    if grep -q "your-domain.com" "$ENV_FILE"; then
        warning "Using localhost domains - update for production"
    fi
    
    success "Environment validation passed"
}

# Security checks
security_checks() {
    log "Performing security checks..."
    
    # Check for development features (warn in development)
    if grep -q "ENABLE_DEBUG_MODE=true" "$ENV_FILE"; then
        warning "DEBUG_MODE is enabled - disable for production"
    fi
    
    if grep -q "ENABLE_TEST_ENDPOINTS=true" "$ENV_FILE"; then
        warning "TEST_ENDPOINTS are enabled - disable for production"
    fi
    
    # Check SSL configuration (optional in development)
    if [[ ! -f "/etc/ssl/certs/app-cert.pem" ]] || [[ ! -f "/etc/ssl/private/app-key.pem" ]]; then
        log "SSL certificates not found - using HTTP for development"
    fi
    
    # Check firewall rules
    if ! command -v ufw &> /dev/null; then
        warning "UFW firewall not found. Consider installing for additional security."
    fi
    
    success "Security checks completed"
}

# Backup existing deployment
backup_existing() {
    log "Creating backup of existing deployment..."
    
    mkdir -p "$BACKUP_DIR"
    BACKUP_NAME="backup-$(date +'%Y%m%d-%H%M%S')"
    BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"
    
    # Backup database
    if docker-compose exec -T database pg_dump -U postgres fs_reconciliation_prod > "$BACKUP_PATH.sql" 2>/dev/null; then
        log "Database backup created: $BACKUP_PATH.sql"
    else
        warning "Failed to create database backup"
    fi
    
    # Backup configuration
    cp "$ENV_FILE" "$BACKUP_PATH.env"
    cp docker-compose.yml "$BACKUP_PATH-docker-compose.yml"
    
    # Cleanup old backups (keep last 7 days)
    find "$BACKUP_DIR" -name "backup-*" -mtime +7 -delete
    
    success "Backup completed: $BACKUP_PATH"
}

# Health check function
health_check() {
    local service=$1
    local max_attempts=30
    local attempt=1
    
    log "Checking health of $service..."
    
    while [[ $attempt -le $max_attempts ]]; do
        if docker-compose ps "$service" | grep -q "Up"; then
            success "$service is healthy"
            return 0
        fi
        
        log "Attempt $attempt/$max_attempts: $service not ready yet..."
        sleep 2
        ((attempt++))
    done
    
    error "$service failed health check after $max_attempts attempts"
}

# Deploy services
deploy_services() {
    log "Starting production deployment..."
    
    # Stop existing services
    log "Stopping existing services..."
    docker-compose down --remove-orphans
    
    # Pull latest images
    log "Pulling latest Docker images..."
    docker-compose pull
    
    # Build services with production configuration
    log "Building services for production..."
    docker-compose build --no-cache
    
    # Start services
    log "Starting services..."
    docker-compose up -d
    
    # Wait for services to be ready
    log "Waiting for services to be ready..."
    sleep 10
    
    # Health checks
    health_check "database"
    health_check "redis"
    health_check "api-service"
    health_check "ui-service"
    health_check "langgraph-agent"
    
    success "All services deployed successfully"
}

# Database migration
run_migrations() {
    log "Running database migrations..."
    
    if docker-compose exec -T api-service alembic upgrade head; then
        success "Database migrations completed"
    else
        error "Database migration failed"
    fi
}

# Security hardening
security_hardening() {
    log "Applying security hardening..."
    
    # Set proper file permissions
    chmod 600 "$ENV_FILE"
    chmod 644 docker-compose.yml
    
    # Configure firewall rules (if UFW is available) - skip in development
    if command -v ufw &> /dev/null && [[ "$ENVIRONMENT" == "production" ]]; then
        log "Configuring firewall rules..."
        sudo ufw allow 22/tcp  # SSH
        sudo ufw allow 80/tcp  # HTTP
        sudo ufw allow 443/tcp # HTTPS
        sudo ufw allow 8000/tcp # API
        sudo ufw allow 3000/tcp # UI
        sudo ufw --force enable
    fi
    
    # Disable unnecessary services (skip in development)
    if [[ "$ENVIRONMENT" == "production" ]]; then
        sudo systemctl disable bluetooth.service 2>/dev/null || true
        sudo systemctl disable cups.service 2>/dev/null || true
    fi
    
    success "Security hardening completed"
}

# Monitoring setup
setup_monitoring() {
    log "Setting up monitoring..."
    
    # Create monitoring directories
    sudo mkdir -p /var/log/fs-reconciliation
    sudo mkdir -p /var/uploads/fs-reconciliation
    sudo mkdir -p /var/backups/fs-reconciliation
    
    # Set proper permissions
    sudo chown -R $USER:$USER /var/log/fs-reconciliation
    sudo chown -R $USER:$USER /var/uploads/fs-reconciliation
    sudo chown -R $USER:$USER /var/backups/fs-reconciliation
    
    # Setup log rotation
    sudo tee /etc/logrotate.d/fs-reconciliation > /dev/null <<EOF
/var/log/fs-reconciliation/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
}
EOF
    
    success "Monitoring setup completed"
}

# Performance optimization
optimize_performance() {
    log "Applying performance optimizations..."
    
    # Configure system limits (skip in development)
    if [[ "$ENVIRONMENT" == "production" ]]; then
        sudo tee -a /etc/security/limits.conf > /dev/null <<EOF
# FS Reconciliation Agents limits
$USER soft nofile 65536
$USER hard nofile 65536
$USER soft nproc 32768
$USER hard nproc 32768
EOF
        
        # Configure kernel parameters
        sudo tee -a /etc/sysctl.conf > /dev/null <<EOF
# FS Reconciliation Agents kernel optimizations
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 1200
net.ipv4.tcp_max_tw_buckets = 400000
net.ipv4.tcp_tw_reuse = 1
net.ipv4.ip_local_port_range = 1024 65535
vm.swappiness = 10
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5
EOF
        
        # Apply kernel parameters
        sudo sysctl -p
    fi
    
    success "Performance optimizations applied"
}

# Final verification
final_verification() {
    log "Performing final verification..."
    
    # Check all services are running
    if docker-compose ps | grep -q "Up"; then
        success "All services are running"
    else
        error "Some services are not running"
    fi
    
    # Test API health
    if curl -f -s http://localhost:8000/health > /dev/null; then
        success "API health check passed"
    else
        error "API health check failed"
    fi
    
    # Test UI accessibility
    if curl -f -s http://localhost:3000 > /dev/null; then
        success "UI accessibility check passed"
    else
        error "UI accessibility check failed"
    fi
    
    # Check disk space
    DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    if [[ $DISK_USAGE -lt 80 ]]; then
        success "Disk space is adequate: ${DISK_USAGE}% used"
    else
        warning "Disk space is low: ${DISK_USAGE}% used"
    fi
    
    # Check memory usage
    MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
    if [[ $MEMORY_USAGE -lt 80 ]]; then
        success "Memory usage is adequate: ${MEMORY_USAGE}% used"
    else
        warning "Memory usage is high: ${MEMORY_USAGE}% used"
    fi
    
    success "Final verification completed"
}

# Main deployment function
main() {
    log "Starting FS Reconciliation Agents production deployment..."
    
    # Change to project directory
    cd "$PROJECT_ROOT"
    
    # Run deployment steps
    check_root
    validate_environment
    security_checks
    backup_existing
    setup_monitoring
    optimize_performance
    deploy_services
    run_migrations
    security_hardening
    final_verification
    
    success "Production deployment completed successfully!"
    log "Application is now available at:"
    log "  - UI: https://your-domain.com"
    log "  - API: https://api.your-domain.com"
    log "  - Monitoring: https://monitoring.your-domain.com"
    
    # Display service status
    echo
    log "Service Status:"
    docker-compose ps
}

# Run main function
main "$@" 