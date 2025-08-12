# FS Reconciliation Agents - Technical Documentation

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [System Requirements](#system-requirements)
3. [Installation and Deployment](#installation-and-deployment)
4. [Configuration](#configuration)
5. [API Documentation](#api-documentation)
6. [Database Schema](#database-schema)
7. [Monitoring and Logging](#monitoring-and-logging)
8. [Security](#security)
9. [Performance Optimization](#performance-optimization)
10. [Troubleshooting](#troubleshooting)

## Architecture Overview

### System Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React UI      │    │   FastAPI       │    │   LangGraph     │
│   (Frontend)    │◄──►│   (Backend)     │◄──►│   (AI Agents)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Nginx         │    │   PostgreSQL    │    │   Redis Cache   │
│   (Reverse      │    │   (Database)    │    │   (Caching)     │
│    Proxy)       │    └─────────────────┘    └─────────────────┘
└─────────────────┘
         │
         ▼
┌─────────────────┐
│   Prometheus    │
│   + Grafana     │
│   (Monitoring)  │
└─────────────────┘
```

### Component Description

#### Frontend (React)
- **Technology**: React 18 with TypeScript
- **UI Framework**: Material-UI (MUI)
- **State Management**: React Query + Context API
- **Routing**: React Router
- **Charts**: Recharts

#### Backend (FastAPI)
- **Technology**: FastAPI with Python 3.11+
- **Authentication**: JWT tokens
- **Validation**: Pydantic models
- **Documentation**: Auto-generated OpenAPI/Swagger

#### AI Agents (LangGraph)
- **Framework**: LangGraph for workflow orchestration
- **LLM**: OpenAI GPT-4o-mini
- **Agents**: Data Ingestion, Normalization, Matching, Exception Identification, Resolution

#### Database (PostgreSQL)
- **Version**: PostgreSQL 15+
- **ORM**: SQLAlchemy with async support
- **Migrations**: Alembic
- **Connection Pooling**: asyncpg

#### Cache (Redis)
- **Version**: Redis 7+
- **Use Cases**: Session storage, API caching, job queues
- **Persistence**: AOF (Append-Only File)

#### Reverse Proxy (Nginx)
- **Version**: Nginx Alpine
- **Features**: Load balancing, SSL termination, rate limiting
- **Security**: Security headers, CORS configuration

#### Monitoring (Prometheus + Grafana)
- **Metrics Collection**: Prometheus
- **Visualization**: Grafana
- **Alerting**: Prometheus AlertManager

## System Requirements

### Minimum Requirements
- **CPU**: 4 cores
- **RAM**: 8GB
- **Storage**: 50GB SSD
- **Network**: 100Mbps

### Recommended Requirements
- **CPU**: 8+ cores
- **RAM**: 16GB+
- **Storage**: 100GB+ SSD
- **Network**: 1Gbps

### Software Requirements
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **OpenSSL**: For SSL certificate generation
- **Git**: For version control

## Installation and Deployment

### Quick Start
```bash
# Clone the repository
git clone <repository-url>
cd fs-reconciliation-agents

# Set environment variables
cp .env.example .env
# Edit .env with your configuration

# Deploy the application
./scripts/deploy.sh
```

### Manual Deployment
```bash
# Build and start services
docker-compose -f docker-compose.prod.yml up -d

# Run database migrations
docker-compose -f docker-compose.prod.yml exec api-service alembic upgrade head

# Check service health
curl http://localhost:8000/health
```

### Environment Variables

#### Required Variables
```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Database Configuration
DATABASE_URL=postgresql://fs_user:fs_password@database:5432/fs_reconciliation
DB_USER=fs_user
DB_PASSWORD=fs_password

# Redis Configuration
REDIS_URL=redis://redis:6379

# Security
SECRET_KEY=your_secret_key_here
JWT_SECRET_KEY=your_jwt_secret_key_here

# Grafana
GRAFANA_PASSWORD=admin
```

#### Optional Variables
```bash
# Logging
LOG_LEVEL=INFO
ENVIRONMENT=production

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# UI Configuration
REACT_APP_API_URL=http://localhost:8000
REACT_APP_ENVIRONMENT=production
```

## Configuration

### Database Configuration
```yaml
# config/database.yaml
database:
  host: database
  port: 5432
  name: fs_reconciliation
  user: fs_user
  password: fs_password
  
  # Connection pooling
  pool_size: 20
  max_overflow: 30
  pool_timeout: 30
  pool_recycle: 3600
  
  # SSL configuration
  ssl_mode: prefer
  
  # Performance tuning
  statement_timeout: 30000
  idle_in_transaction_session_timeout: 300000
```

### Redis Configuration
```yaml
# config/redis.yaml
redis:
  host: redis
  port: 6379
  db: 0
  
  # Connection pooling
  max_connections: 50
  socket_timeout: 5
  socket_connect_timeout: 5
  
  # Memory management
  maxmemory: 512mb
  maxmemory_policy: allkeys-lru
```

### OpenAI Configuration
```yaml
# config/openai_config.yaml
openai:
  api_key: ${OPENAI_API_KEY}
  model: gpt-4o-mini-2024-07-18
  fallback_model: gpt-4o-mini-2024-07-18
  max_tokens: 4000
  temperature: 0.1
  timeout: 30
```

## API Documentation

### Authentication
All API endpoints require authentication via JWT tokens.

```bash
# Login
POST /api/auth/login
{
  "email": "user@example.com",
  "password": "password"
}

# Response
{
  "token": "jwt_token_here",
  "user": {
    "id": "user_id",
    "name": "User Name",
    "email": "user@example.com",
    "role": "analyst"
  }
}
```

### Health Check
```bash
GET /health
# Response: {"status": "healthy", "service": "fs-reconciliation-api"}
```

### Exceptions API
```bash
# Get exceptions
GET /api/exceptions?skip=0&limit=100&break_type=security_id_break

# Create exception
POST /api/exceptions
{
  "transaction_id": "uuid",
  "break_type": "security_id_break",
  "severity": "medium",
  "amount": 100000.00,
  "currency": "USD"
}

# Resolve exception
POST /api/exceptions/{exception_id}/resolve
{
  "notes": "Resolution notes",
  "action": "auto_resolve"
}
```

### Data Upload API
```bash
# Upload file
POST /api/data/upload
Content-Type: multipart/form-data
{
  "file": "file_data",
  "data_source": "bloomberg",
  "file_type": "csv"
}

# Batch upload
POST /api/data/upload/batch
{
  "files": ["file1.csv", "file2.xlsx"],
  "data_source": "reuters"
}
```

### Reports API
```bash
# Generate report
POST /api/reports/generate
{
  "report_type": "break_summary",
  "format": "pdf",
  "parameters": {
    "date_from": "2024-01-01",
    "date_to": "2024-12-31"
  }
}
```

## Database Schema

### Core Tables

#### Transactions
```sql
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(255) NOT NULL,
    amount DECIMAL(20,2) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    security_id VARCHAR(50),
    security_name VARCHAR(255),
    trade_date DATE,
    settlement_date DATE,
    market_price DECIMAL(10,4),
    fx_rate DECIMAL(10,6),
    data_source VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Reconciliation Exceptions
```sql
CREATE TABLE reconciliation_exceptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID REFERENCES transactions(id),
    break_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'open',
    amount DECIMAL(20,2),
    currency VARCHAR(3),
    break_details JSONB,
    financial_impact DECIMAL(20,2),
    resolution_notes TEXT,
    assigned_to VARCHAR(100),
    priority VARCHAR(20) DEFAULT 'medium',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Audit Trails
```sql
CREATE TABLE audit_trails (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(100),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Indexes
```sql
-- Performance indexes
CREATE INDEX idx_transactions_external_id ON transactions(external_id);
CREATE INDEX idx_transactions_security_id ON transactions(security_id);
CREATE INDEX idx_transactions_trade_date ON transactions(trade_date);
CREATE INDEX idx_exceptions_break_type ON reconciliation_exceptions(break_type);
CREATE INDEX idx_exceptions_severity ON reconciliation_exceptions(severity);
CREATE INDEX idx_exceptions_status ON reconciliation_exceptions(status);
CREATE INDEX idx_exceptions_created_at ON reconciliation_exceptions(created_at);
```

## Monitoring and Logging

### Metrics Collection
The application exposes metrics in Prometheus format at `/metrics`:

```bash
# API metrics
http_requests_total{method="GET", endpoint="/health"}
http_request_duration_seconds{method="POST", endpoint="/api/exceptions"}

# Business metrics
exceptions_processed_total{break_type="security_id_break"}
file_uploads_total{status="success"}
resolution_time_seconds{severity="high"}
```

### Logging Configuration
```python
# Logging levels
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Log formats
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Log handlers
- Console handler for development
- File handler for production
- Structured logging for analysis
```

### Health Checks
```bash
# API health
curl http://localhost:8000/health

# Database health
docker-compose exec database pg_isready -U fs_user

# Redis health
docker-compose exec redis redis-cli ping
```

## Security

### Authentication
- **JWT Tokens**: Stateless authentication
- **Password Hashing**: bcrypt with salt
- **Session Management**: Redis-based sessions
- **Token Expiration**: Configurable TTL

### Authorization
- **Role-Based Access Control (RBAC)**: User roles and permissions
- **Resource-Level Permissions**: Fine-grained access control
- **API Rate Limiting**: Per-user and per-endpoint limits

### Data Protection
- **Encryption at Rest**: Database encryption
- **Encryption in Transit**: TLS/SSL for all communications
- **Data Masking**: Sensitive data protection
- **Audit Logging**: Complete activity tracking

### Network Security
- **Firewall Rules**: Restrict access to necessary ports
- **VPN Access**: Secure remote access
- **SSL/TLS**: HTTPS for all web traffic
- **Security Headers**: XSS, CSRF protection

## Performance Optimization

### Database Optimization
```sql
-- Query optimization
EXPLAIN ANALYZE SELECT * FROM reconciliation_exceptions WHERE break_type = 'security_id_break';

-- Partitioning for large tables
CREATE TABLE reconciliation_exceptions_partitioned (
    -- same structure
) PARTITION BY RANGE (created_at);

-- Connection pooling
-- Configured in database.yaml
```

### Caching Strategy
```python
# Redis caching layers
1. API response caching (5 minutes)
2. Database query caching (10 minutes)
3. Session storage (30 minutes)
4. File processing cache (1 hour)
```

### Application Optimization
```python
# Async processing
- Database operations: async/await
- File processing: background tasks
- Report generation: queue-based

# Memory management
- Connection pooling
- Garbage collection tuning
- Memory monitoring
```

### Load Balancing
```nginx
# Nginx upstream configuration
upstream api_backend {
    server api-service:8000;
    keepalive 32;
}

# Rate limiting
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
```

## Troubleshooting

### Common Issues

#### Database Connection Issues
```bash
# Check database status
docker-compose exec database pg_isready -U fs_user

# Check connection logs
docker-compose logs database

# Reset database
docker-compose exec database psql -U fs_user -d fs_reconciliation -c "SELECT 1;"
```

#### Redis Connection Issues
```bash
# Check Redis status
docker-compose exec redis redis-cli ping

# Check Redis memory
docker-compose exec redis redis-cli info memory

# Clear Redis cache
docker-compose exec redis redis-cli FLUSHALL
```

#### API Service Issues
```bash
# Check API logs
docker-compose logs api-service

# Restart API service
docker-compose restart api-service

# Check API health
curl http://localhost:8000/health
```

#### UI Service Issues
```bash
# Check UI logs
docker-compose logs ui-service

# Rebuild UI
docker-compose build ui-service
docker-compose up -d ui-service
```

### Performance Issues

#### High CPU Usage
```bash
# Check container resource usage
docker stats

# Optimize database queries
docker-compose exec database psql -U fs_user -d fs_reconciliation -c "SELECT * FROM pg_stat_activity;"

# Check slow queries
docker-compose exec database psql -U fs_user -d fs_reconciliation -c "SELECT * FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"
```

#### High Memory Usage
```bash
# Check memory usage
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Clear Redis cache
docker-compose exec redis redis-cli FLUSHALL

# Restart services
docker-compose restart
```

#### Slow Response Times
```bash
# Check API response times
curl -w "@curl-format.txt" -o /dev/null -s "http://localhost:8000/health"

# Monitor network latency
docker-compose exec api-service ping database

# Check database performance
docker-compose exec database psql -U fs_user -d fs_reconciliation -c "SELECT * FROM pg_stat_database;"
```

### Log Analysis
```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f api-service

# Search logs
docker-compose logs | grep "ERROR"

# Export logs
docker-compose logs > application.log
```

### Backup and Recovery

#### Database Backup
```bash
# Create backup
docker-compose exec database pg_dump -U fs_user fs_reconciliation > backup.sql

# Restore backup
docker-compose exec -T database psql -U fs_user fs_reconciliation < backup.sql
```

#### Application Backup
```bash
# Backup data directory
tar -czf data_backup.tar.gz data/

# Backup configuration
tar -czf config_backup.tar.gz config/ scripts/ docker-compose.prod.yml
```

---

For additional technical support, please refer to the development team or create an issue in the project repository. 