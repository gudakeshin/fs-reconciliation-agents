# FS Reconciliation Agents - Enhancements Deployment Guide

## 🚀 **Quick Start Deployment**

### **Option 1: Automated Deployment (Recommended)**

Run the automated deployment script:

```bash
# Make sure you're in the project root directory
cd "FS Reconciliation Agents"

# Run the deployment script
./scripts/deploy_enhancements.sh
```

This script will automatically:
- ✅ Backup your current system
- ✅ Deploy all database optimizations
- ✅ Set up Redis caching
- ✅ Deploy API v2 with enhancements
- ✅ Deploy UI improvements
- ✅ Set up AI services
- ✅ Configure monitoring
- ✅ Run comprehensive health checks

### **Option 2: Manual Step-by-Step Deployment**

If you prefer manual deployment, follow these steps:

---

## 📋 **Prerequisites**

Before deploying, ensure you have:

- ✅ Docker and Docker Compose installed
- ✅ At least 4GB RAM available
- ✅ 10GB free disk space
- ✅ Current system running and accessible

---

## 🔧 **Step-by-Step Manual Deployment**

### **Step 1: Backup Current System**

```bash
# Create backup directory
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup database
docker-compose exec -T database pg_dump -U reconciliation_user reconciliation_db > "$BACKUP_DIR/database_backup.sql"

# Backup configuration
cp -r config "$BACKUP_DIR/"
cp docker-compose.yml "$BACKUP_DIR/"
```

### **Step 2: Deploy Database Optimizations**

```bash
# Start database service
docker-compose up -d database

# Wait for database to be ready
sleep 10

# Run optimization script
docker exec fs-reconciliation-db psql -U reconciliation_user -d reconciliation_db -f /app/scripts/database_optimization.sql
```

### **Step 3: Deploy Cache Service**

```bash
# Start Redis service
docker-compose up -d redis

# Test Redis connection
docker exec fs-reconciliation-redis redis-cli ping
```

### **Step 4: Deploy API v2**

```bash
# Create API v2 override
cat > docker-compose.v2.yml << 'EOF'
version: '3.8'

services:
  api-service:
    build:
      context: .
      dockerfile: docker/api-service/Dockerfile
    environment:
      - API_VERSION=v2
      - ENABLE_CACHE=true
      - ENABLE_WEBSOCKETS=true
      - ENABLE_RATE_LIMITING=true
    volumes:
      - ./src/api/v2:/app/src/api/v2
      - ./src/core/services/caching:/app/src/core/services/caching
      - ./src/core/services/ai:/app/src/core/services/ai
    command: ["python", "-m", "uvicorn", "src.api.v2.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
EOF

# Rebuild and start API v2
docker-compose -f docker-compose.yml -f docker-compose.v2.yml build api-service
docker-compose -f docker-compose.yml -f docker-compose.v2.yml up -d api-service
```

### **Step 5: Deploy UI Enhancements**

```bash
# Install new dependencies
cd src/ui
npm install recharts @mui/x-date-pickers date-fns @mui/lab

# Build enhanced UI
npm run build

cd ../..

# Rebuild and start UI service
docker-compose build ui-service
docker-compose up -d ui-service
```

### **Step 6: Deploy AI Services**

```bash
# Create models directory
mkdir -p models

# Install AI dependencies
docker-compose exec api-service pip install scikit-learn joblib pandas numpy
```

### **Step 7: Deploy Monitoring**

```bash
# Start monitoring services
docker-compose up -d prometheus grafana
```

---

## 🧪 **Verification & Testing**

### **Health Checks**

```bash
# Check all services are running
docker-compose ps

# Test API health
curl http://localhost:8000/health

# Test API v2
curl http://localhost:8000/

# Test UI
curl http://localhost:3000

# Test Redis
docker exec fs-reconciliation-redis redis-cli ping

# Test monitoring
curl http://localhost:9090/-/healthy  # Prometheus
curl http://localhost:3001/api/health # Grafana
```

### **Feature Testing**

1. **API v2 Features**:
   - Visit http://localhost:8000/docs for enhanced API documentation
   - Test rate limiting by making multiple requests
   - Check WebSocket endpoints at http://localhost:8000/ws/status

2. **UI Enhancements**:
   - Visit http://localhost:3000
   - Test advanced filtering on the Exception Management page
   - Check data visualization components
   - Test mobile responsiveness

3. **Caching**:
   - Monitor cache performance in Redis
   - Check API response times (should be significantly faster)

4. **AI Features**:
   - Upload test data to see predictive analytics in action
   - Check AI recommendations in the UI

---

## 📊 **Access URLs**

After successful deployment, access your enhanced system at:

| Service | URL | Credentials |
|---------|-----|-------------|
| **UI** | http://localhost:3000 | - |
| **API v2** | http://localhost:8000 | - |
| **API Docs** | http://localhost:8000/docs | - |
| **Grafana** | http://localhost:3001 | admin/admin |
| **Prometheus** | http://localhost:9090 | - |

---

## 🔍 **Troubleshooting**

### **Common Issues**

#### **1. Database Optimization Fails**
```bash
# Check database logs
docker-compose logs database

# Manually run optimization
docker exec -it fs-reconciliation-db psql -U reconciliation_user -d reconciliation_db -c "SELECT version();"
```

#### **2. Redis Connection Issues**
```bash
# Check Redis logs
docker-compose logs redis

# Test Redis manually
docker exec -it fs-reconciliation-redis redis-cli ping
```

#### **3. API v2 Not Starting**
```bash
# Check API logs
docker-compose logs api-service

# Check if v2 files exist
ls -la src/api/v2/
```

#### **4. UI Build Fails**
```bash
# Check Node.js version
node --version

# Clear npm cache
npm cache clean --force

# Reinstall dependencies
cd src/ui && rm -rf node_modules package-lock.json && npm install
```

#### **5. Port Conflicts**
```bash
# Check what's using the ports
lsof -i :3000
lsof -i :8000
lsof -i :3001
lsof -i :9090

# Stop conflicting services
sudo lsof -ti:3000 | xargs kill -9
```

### **Rollback Procedure**

If you need to rollback to the previous version:

```bash
# Stop enhanced services
docker-compose down

# Restore from backup
BACKUP_DIR="backup_YYYYMMDD_HHMMSS"  # Replace with actual backup directory
cp -r "$BACKUP_DIR/config" ./
cp "$BACKUP_DIR/docker-compose.yml" ./

# Restore database
docker-compose up -d database
docker exec -i fs-reconciliation-db psql -U reconciliation_user -d reconciliation_db < "$BACKUP_DIR/database_backup.sql"

# Start original services
docker-compose up -d
```

---

## 📈 **Performance Monitoring**

### **Grafana Dashboards**

1. **FS Reconciliation Dashboard**: http://localhost:3001
   - Login: admin/admin
   - View real-time metrics and performance data

2. **Key Metrics to Monitor**:
   - API response times
   - Database query performance
   - Cache hit rates
   - Exception processing rates
   - User activity

### **Performance Benchmarks**

After deployment, you should see:

- **API Response Time**: < 200ms average
- **Database Queries**: < 100ms for common operations
- **Cache Hit Rate**: > 80%
- **UI Load Time**: < 2 seconds

---

## 🎯 **Post-Deployment Checklist**

- [ ] All services are running (`docker-compose ps`)
- [ ] API v2 is accessible (http://localhost:8000/health)
- [ ] UI is working (http://localhost:3000)
- [ ] Advanced filtering is functional
- [ ] Data visualization components are working
- [ ] Caching is active (faster response times)
- [ ] Monitoring is accessible (Grafana/Prometheus)
- [ ] AI features are operational
- [ ] Mobile responsiveness is working
- [ ] WebSocket connections are established

---

## 🚀 **Next Steps**

1. **User Training**: Train users on new features
2. **Performance Monitoring**: Set up alerts in Grafana
3. **Feedback Collection**: Gather user feedback
4. **Optimization**: Fine-tune based on usage patterns
5. **Documentation**: Update user documentation

---

## 📞 **Support**

If you encounter issues:

1. Check the troubleshooting section above
2. Review service logs: `docker-compose logs [service-name]`
3. Check the enhancement documentation: `ENHANCEMENTS_IMPLEMENTATION_SUMMARY.md`
4. Verify system requirements and prerequisites

---

**Deployment Status**: ✅ **Ready for Production**

The enhanced FS Reconciliation Agents system is now ready for production use with all the latest improvements and optimizations!
