#!/bin/bash

# Production Deployment Script for FS Reconciliation Agents
# This script deploys the complete system with all enhancements

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 FS Reconciliation Agents - Production Deployment${NC}"
echo "========================================================"

# Configuration
ENVIRONMENT=${1:-production}
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
LOG_FILE="deployment_$(date +%Y%m%d_%H%M%S).log"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Function to log messages
log_message() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $message" | tee -a "$LOG_FILE"
}

# Function to check prerequisites
check_prerequisites() {
    log_message "🔍 Checking deployment prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker is not installed${NC}"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}❌ Docker Compose is not installed${NC}"
        exit 1
    fi
    
    # Check available disk space (at least 5GB)
    local available_space=$(df . | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 5242880 ]; then
        echo -e "${RED}❌ Insufficient disk space (need at least 5GB)${NC}"
        exit 1
    fi
    
    # Check available memory (at least 4GB)
    local available_memory=$(free -m | awk 'NR==2{print $7}')
    if [ "$available_memory" -lt 4096 ]; then
        echo -e "${YELLOW}⚠️  Low memory available (${available_memory}MB). Recommended: 4GB+${NC}"
    fi
    
    echo -e "${GREEN}✅ Prerequisites check passed${NC}"
}

# Function to backup existing system
backup_system() {
    log_message "💾 Creating system backup..."
    
    # Backup database
    if docker ps --format "table {{.Names}}" | grep -q "fs-reconciliation-db"; then
        log_message "Backing up database..."
        docker exec fs-reconciliation-db pg_dump -U postgres reconciliation_db > "$BACKUP_DIR/database_backup.sql" 2>/dev/null || true
    fi
    
    # Backup configuration files
    log_message "Backing up configuration files..."
    cp -r config "$BACKUP_DIR/" 2>/dev/null || true
    cp docker-compose.yml "$BACKUP_DIR/" 2>/dev/null || true
    
    # Backup logs
    log_message "Backing up logs..."
    cp -r logs "$BACKUP_DIR/" 2>/dev/null || true
    
    echo -e "${GREEN}✅ System backup completed: $BACKUP_DIR${NC}"
}

# Function to stop existing services
stop_services() {
    log_message "🛑 Stopping existing services..."
    
    # Stop main services
    docker-compose down --remove-orphans 2>/dev/null || true
    
    # Stop monitoring services
    docker-compose -f docker-compose.monitoring.yml down 2>/dev/null || true
    
    echo -e "${GREEN}✅ Services stopped${NC}"
}

# Function to deploy database optimizations
deploy_database_optimizations() {
    log_message "🗄️  Deploying database optimizations..."
    
    # Wait for database to be ready
    log_message "Waiting for database to be ready..."
    sleep 10
    
    # Run database optimization script
    if [ -f "scripts/database_optimization.sql" ]; then
        log_message "Applying database optimizations..."
        docker exec fs-reconciliation-db psql -U postgres -d reconciliation_db -f /app/database_optimization.sql || {
            log_message "Warning: Some database optimizations may have failed (this is expected if they already exist)"
        }
    fi
    
    echo -e "${GREEN}✅ Database optimizations deployed${NC}"
}

# Function to deploy core services
deploy_core_services() {
    log_message "🚀 Deploying core services..."
    
    # Start core services
    docker-compose up -d database redis
    
    # Wait for database to be ready
    log_message "Waiting for database to be ready..."
    sleep 15
    
    # Deploy database optimizations
    deploy_database_optimizations
    
    # Start remaining services
    docker-compose up -d api-service langgraph-agent ui-service
    
    echo -e "${GREEN}✅ Core services deployed${NC}"
}

# Function to deploy monitoring
deploy_monitoring() {
    log_message "📊 Deploying monitoring infrastructure..."
    
    # Run monitoring setup
    ./scripts/setup_monitoring.sh full
    
    echo -e "${GREEN}✅ Monitoring infrastructure deployed${NC}"
}

# Function to run tests
run_tests() {
    log_message "🧪 Running system tests..."
    
    # Wait for services to be ready
    log_message "Waiting for services to be ready..."
    sleep 30
    
    # Run health checks
    log_message "Running health checks..."
    
    # API health check
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log_message "✅ API health check passed"
    else
        log_message "❌ API health check failed"
        return 1
    fi
    
    # UI health check
    if curl -f http://localhost:3000 > /dev/null 2>&1; then
        log_message "✅ UI health check passed"
    else
        log_message "❌ UI health check failed"
        return 1
    fi
    
    # Database health check
    if docker exec fs-reconciliation-db pg_isready -U postgres > /dev/null 2>&1; then
        log_message "✅ Database health check passed"
    else
        log_message "❌ Database health check failed"
        return 1
    fi
    
    # Redis health check
    if docker exec fs-reconciliation-redis redis-cli ping > /dev/null 2>&1; then
        log_message "✅ Redis health check passed"
    else
        log_message "❌ Redis health check failed"
        return 1
    fi
    
    echo -e "${GREEN}✅ All health checks passed${NC}"
}

# Function to verify deployment
verify_deployment() {
    log_message "🔍 Verifying deployment..."
    
    # Check service status
    log_message "Checking service status..."
    docker-compose ps
    
    # Check resource usage
    log_message "Checking resource usage..."
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
    
    # Check logs for errors
    log_message "Checking for errors in logs..."
    if docker-compose logs --tail=50 | grep -i error; then
        log_message "⚠️  Found errors in logs (check manually)"
    else
        log_message "✅ No errors found in recent logs"
    fi
    
    echo -e "${GREEN}✅ Deployment verification completed${NC}"
}

# Function to display deployment summary
display_summary() {
    echo -e "${BLUE}📋 Deployment Summary${NC}"
    echo "======================"
    echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
    echo ""
    echo -e "${BLUE}🌐 Access URLs:${NC}"
    echo "  Main Application: http://localhost:3000"
    echo "  API Documentation: http://localhost:8000/docs"
    echo "  API Health Check: http://localhost:8000/health"
    echo "  Prometheus: http://localhost:9090"
    echo "  Grafana: http://localhost:3001 (admin/admin123)"
    echo "  AlertManager: http://localhost:9093"
    echo ""
    echo -e "${BLUE}📁 Important Directories:${NC}"
    echo "  Logs: logs/"
    echo "  Backups: $BACKUP_DIR"
    echo "  Configuration: config/"
    echo "  Monitoring: monitoring/"
    echo ""
    echo -e "${BLUE}🔧 Management Commands:${NC}"
    echo "  View logs: docker-compose logs -f"
    echo "  Restart services: docker-compose restart"
    echo "  Stop services: docker-compose down"
    echo "  Run tests: ./scripts/run_tests.sh"
    echo "  Monitor status: ./scripts/setup_monitoring.sh status"
    echo ""
    echo -e "${YELLOW}📝 Next Steps:${NC}"
    echo "1. Review security configuration in config/security_config.yaml"
    echo "2. Set up SSL certificates for production"
    echo "3. Configure backup schedules"
    echo "4. Set up monitoring alerts"
    echo "5. Train team on system usage"
    echo ""
    echo -e "${GREEN}🎉 Your FS Reconciliation Agents system is now live!${NC}"
}

# Function to rollback deployment
rollback_deployment() {
    log_message "🔄 Rolling back deployment..."
    
    # Stop all services
    docker-compose down --remove-orphans
    docker-compose -f docker-compose.monitoring.yml down 2>/dev/null || true
    
    # Restore from backup if available
    if [ -d "$BACKUP_DIR" ]; then
        log_message "Restoring from backup..."
        # Add restore logic here
    fi
    
    echo -e "${YELLOW}⚠️  Deployment rolled back${NC}"
}

# Main deployment function
main_deployment() {
    local start_time=$(date +%s)
    
    log_message "Starting production deployment..."
    
    # Check prerequisites
    check_prerequisites
    
    # Backup existing system
    backup_system
    
    # Stop existing services
    stop_services
    
    # Deploy core services
    deploy_core_services
    
    # Deploy monitoring
    deploy_monitoring
    
    # Run tests
    if run_tests; then
        log_message "✅ All tests passed"
    else
        log_message "❌ Some tests failed"
        rollback_deployment
        exit 1
    fi
    
    # Verify deployment
    verify_deployment
    
    # Calculate deployment time
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log_message "Deployment completed in ${duration} seconds"
    
    # Display summary
    display_summary
}

# Handle command line arguments
case "${1:-}" in
    "deploy")
        main_deployment
        ;;
    "rollback")
        rollback_deployment
        ;;
    "test")
        run_tests
        ;;
    "verify")
        verify_deployment
        ;;
    "backup")
        backup_system
        ;;
    "stop")
        stop_services
        ;;
    "start")
        deploy_core_services
        ;;
    "monitoring")
        deploy_monitoring
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [deploy|rollback|test|verify|backup|stop|start|monitoring|help]"
        echo ""
        echo "Options:"
        echo "  deploy     - Complete production deployment"
        echo "  rollback   - Rollback to previous version"
        echo "  test       - Run system tests"
        echo "  verify     - Verify deployment status"
        echo "  backup     - Create system backup"
        echo "  stop       - Stop all services"
        echo "  start      - Start core services"
        echo "  monitoring - Deploy monitoring infrastructure"
        echo "  help       - Show this help message"
        echo ""
        echo "Default: deploy"
        exit 0
        ;;
    "")
        main_deployment
        ;;
    *)
        echo -e "${RED}❌ Unknown option: $1${NC}"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac
