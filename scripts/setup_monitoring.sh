#!/bin/bash

# Monitoring Setup Script for FS Reconciliation Agents
# This script sets up Prometheus, Grafana, and monitoring dashboards

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔧 Setting up Monitoring Infrastructure${NC}"
echo "=============================================="

# Configuration
PROMETHEUS_PORT=9090
GRAFANA_PORT=3001
ALERTMANAGER_PORT=9093

# Create monitoring directories
mkdir -p monitoring/prometheus/rules
mkdir -p monitoring/grafana/provisioning/dashboards
mkdir -p monitoring/grafana/provisioning/datasources
mkdir -p monitoring/alertmanager

echo -e "${YELLOW}📁 Creating monitoring directories...${NC}"

# Create Prometheus configuration
cat > monitoring/prometheus.yml << EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "rules/*.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  - job_name: 'fs-reconciliation-api'
    static_configs:
      - targets: ['api-service:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s

  - job_name: 'fs-reconciliation-db'
    static_configs:
      - targets: ['database:5432']
    scrape_interval: 30s

  - job_name: 'fs-reconciliation-redis'
    static_configs:
      - targets: ['redis:6379']
    scrape_interval: 30s

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
    scrape_interval: 15s
EOF

# Create alerting rules
cat > monitoring/prometheus/rules/alerts.yml << EOF
groups:
  - name: fs-reconciliation-alerts
    rules:
      - alert: HighCPUUsage
        expr: cpu_usage_percent > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage detected"
          description: "CPU usage is above 80% for more than 5 minutes"

      - alert: HighMemoryUsage
        expr: memory_usage_percent > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage detected"
          description: "Memory usage is above 85% for more than 5 minutes"

      - alert: HighResponseTime
        expr: rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m]) > 2
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High API response time"
          description: "Average API response time is above 2 seconds"

      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is above 10% for more than 2 minutes"

      - alert: DatabaseConnectionIssues
        expr: database_connections > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High database connection usage"
          description: "Database connections are above 80% of capacity"

      - alert: CacheHitRatioLow
        expr: cache_hit_ratio < 70
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Low cache hit ratio"
          description: "Cache hit ratio is below 70% for more than 10 minutes"

      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service is down"
          description: "A service has been down for more than 1 minute"
EOF

# Create Grafana datasource configuration
cat > monitoring/grafana/provisioning/datasources/prometheus.yml << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
EOF

# Create Grafana dashboard provisioning
cat > monitoring/grafana/provisioning/dashboards/dashboards.yml << EOF
apiVersion: 1

providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
EOF

# Create AlertManager configuration
cat > monitoring/alertmanager/alertmanager.yml << EOF
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'

receivers:
  - name: 'web.hook'
    webhook_configs:
      - url: 'http://127.0.0.1:5001/'

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'dev', 'instance']
EOF

# Create Docker Compose for monitoring
cat > docker-compose.monitoring.yml << EOF
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: fs-reconciliation-prometheus
    ports:
      - "${PROMETHEUS_PORT}:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./monitoring/prometheus/rules:/etc/prometheus/rules
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=200h'
      - '--web.enable-lifecycle'
    networks:
      - fs-reconciliation-network

  grafana:
    image: grafana/grafana:latest
    container_name: fs-reconciliation-grafana
    ports:
      - "${GRAFANA_PORT}:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin123
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards
      - grafana_data:/var/lib/grafana
    networks:
      - fs-reconciliation-network
    depends_on:
      - prometheus

  alertmanager:
    image: prom/alertmanager:latest
    container_name: fs-reconciliation-alertmanager
    ports:
      - "${ALERTMANAGER_PORT}:9093"
    volumes:
      - ./monitoring/alertmanager:/etc/alertmanager
      - alertmanager_data:/alertmanager
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
    networks:
      - fs-reconciliation-network

  node-exporter:
    image: prom/node-exporter:latest
    container_name: fs-reconciliation-node-exporter
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    networks:
      - fs-reconciliation-network

volumes:
  prometheus_data:
  grafana_data:
  alertmanager_data:

networks:
  fs-reconciliation-network:
    external: true
EOF

echo -e "${GREEN}✅ Monitoring configuration files created${NC}"

# Function to start monitoring services
start_monitoring() {
    echo -e "${YELLOW}🚀 Starting monitoring services...${NC}"
    
    # Create network if it doesn't exist
    docker network create fs-reconciliation-network 2>/dev/null || true
    
    # Start monitoring services
    docker-compose -f docker-compose.monitoring.yml up -d
    
    echo -e "${GREEN}✅ Monitoring services started${NC}"
    echo -e "${BLUE}📊 Access URLs:${NC}"
    echo -e "  Prometheus: http://localhost:${PROMETHEUS_PORT}"
    echo -e "  Grafana: http://localhost:${GRAFANA_PORT} (admin/admin123)"
    echo -e "  AlertManager: http://localhost:${ALERTMANAGER_PORT}"
}

# Function to stop monitoring services
stop_monitoring() {
    echo -e "${YELLOW}🛑 Stopping monitoring services...${NC}"
    docker-compose -f docker-compose.monitoring.yml down
    echo -e "${GREEN}✅ Monitoring services stopped${NC}"
}

# Function to check monitoring status
check_status() {
    echo -e "${BLUE}📋 Monitoring Services Status${NC}"
    echo "================================"
    
    services=("prometheus" "grafana" "alertmanager" "node-exporter")
    
    for service in "${services[@]}"; do
        if docker ps --format "table {{.Names}}" | grep -q "fs-reconciliation-${service}"; then
            echo -e "${GREEN}✅ ${service} is running${NC}"
        else
            echo -e "${RED}❌ ${service} is not running${NC}"
        fi
    done
}

# Function to import dashboards
import_dashboards() {
    echo -e "${YELLOW}📊 Importing Grafana dashboards...${NC}"
    
    # Wait for Grafana to be ready
    echo "Waiting for Grafana to be ready..."
    sleep 30
    
    # Import performance dashboard
    curl -X POST \
        -H "Content-Type: application/json" \
        -H "Authorization: Basic YWRtaW46YWRtaW4xMjM=" \
        -d @monitoring/grafana/dashboards/performance-dashboard.json \
        http://localhost:${GRAFANA_PORT}/api/dashboards/db
    
    echo -e "${GREEN}✅ Dashboards imported${NC}"
}

# Function to setup metrics endpoint
setup_metrics_endpoint() {
    echo -e "${YELLOW}🔧 Setting up metrics endpoint...${NC}"
    
    # Add metrics endpoint to API
    cat >> src/api/main.py << 'EOF'

# Metrics endpoint for Prometheus
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    from src.core.services.monitoring.performance_monitor import performance_monitor
    
    # Get system metrics
    system_metrics = performance_monitor.get_system_metrics()
    
    # Format as Prometheus metrics
    metrics = []
    metrics.append(f"# HELP cpu_usage_percent CPU usage percentage")
    metrics.append(f"# TYPE cpu_usage_percent gauge")
    metrics.append(f"cpu_usage_percent {system_metrics.get('cpu_usage', 0)}")
    
    metrics.append(f"# HELP memory_usage_percent Memory usage percentage")
    metrics.append(f"# TYPE memory_usage_percent gauge")
    metrics.append(f"memory_usage_percent {system_metrics.get('memory_usage', 0)}")
    
    metrics.append(f"# HELP disk_usage_percent Disk usage percentage")
    metrics.append(f"# TYPE disk_usage_percent gauge")
    metrics.append(f"disk_usage_percent {system_metrics.get('disk_usage', 0)}")
    
    return Response(content="\n".join(metrics), media_type="text/plain")
EOF
    
    echo -e "${GREEN}✅ Metrics endpoint added to API${NC}"
}

# Main execution
case "${1:-}" in
    "start")
        start_monitoring
        ;;
    "stop")
        stop_monitoring
        ;;
    "restart")
        stop_monitoring
        sleep 2
        start_monitoring
        ;;
    "status")
        check_status
        ;;
    "import")
        import_dashboards
        ;;
    "setup")
        setup_metrics_endpoint
        ;;
    "full")
        setup_metrics_endpoint
        start_monitoring
        sleep 10
        import_dashboards
        check_status
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [start|stop|restart|status|import|setup|full|help]"
        echo ""
        echo "Options:"
        echo "  start   - Start monitoring services"
        echo "  stop    - Stop monitoring services"
        echo "  restart - Restart monitoring services"
        echo "  status  - Check monitoring services status"
        echo "  import  - Import Grafana dashboards"
        echo "  setup   - Setup metrics endpoint in API"
        echo "  full    - Complete setup (setup + start + import)"
        echo "  help    - Show this help message"
        echo ""
        echo "Default: Show help"
        exit 0
        ;;
    "")
        echo -e "${BLUE}📋 Monitoring Setup Complete${NC}"
        echo "================================"
        echo -e "${GREEN}✅ Configuration files created:${NC}"
        echo "  - monitoring/prometheus.yml"
        echo "  - monitoring/prometheus/rules/alerts.yml"
        echo "  - monitoring/grafana/provisioning/"
        echo "  - monitoring/alertmanager/alertmanager.yml"
        echo "  - docker-compose.monitoring.yml"
        echo ""
        echo -e "${YELLOW}Next steps:${NC}"
        echo "1. Run: $0 setup    # Setup metrics endpoint"
        echo "2. Run: $0 start    # Start monitoring services"
        echo "3. Run: $0 import   # Import dashboards"
        echo "4. Run: $0 full     # Complete setup"
        echo ""
        echo -e "${BLUE}Access URLs (after starting):${NC}"
        echo "  Prometheus: http://localhost:${PROMETHEUS_PORT}"
        echo "  Grafana: http://localhost:${GRAFANA_PORT} (admin/admin123)"
        echo "  AlertManager: http://localhost:${ALERTMANAGER_PORT}"
        ;;
    *)
        echo -e "${RED}❌ Unknown option: $1${NC}"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac
