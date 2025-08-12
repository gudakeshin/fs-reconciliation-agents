# FS Reconciliation Agents

A comprehensive, AI-powered financial reconciliation system built with modern technologies for automated bank reconciliation using the LangGraph framework.

## 🚀 Features

### Core Functionality
- **AI-Powered Reconciliation**: Advanced exception detection and classification using Large Language Models
- **Multi-Source Data Integration**: Support for various data sources and formats
- **Real-time Processing**: Fast and efficient transaction matching and reconciliation
- **Comprehensive Audit Trail**: Full traceability of all reconciliation activities
- **Advanced Exception Management**: Intelligent break detection and resolution workflows

### Database Management
- **Comprehensive Database Interface**: Manage all database tables from a single interface
- **Advanced Filtering & Search**: Find specific records quickly with multiple filter options
- **Bulk Operations**: Efficiently manage large datasets with multi-select capabilities
- **Data Analytics**: View table statistics and column analytics
- **Export Capabilities**: Download data for external analysis
- **Real-time Updates**: Automatic refresh and data synchronization

### Governance & Monitoring
- **System Logs**: Comprehensive logging of all system activities
- **Audit Trail**: Detailed audit records for compliance
- **Performance Monitoring**: Real-time system performance metrics
- **User Activity Tracking**: Monitor user actions and system usage

## 🏗️ Architecture

### Technology Stack
- **Backend**: FastAPI (Python) with async/await support
- **Frontend**: React with TypeScript and Material-UI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **AI/ML**: LangGraph framework with OpenAI integration
- **Caching**: Redis for session management and caching
- **Containerization**: Docker with Docker Compose
- **Monitoring**: Prometheus and Grafana

### System Components
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React UI      │    │   FastAPI       │    │   LangGraph     │
│   (TypeScript)  │◄──►│   (Python)      │◄──►│   (AI Agents)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Nginx         │    │   PostgreSQL    │    │   Redis         │
│   (Reverse      │    │   (Database)    │    │   (Cache)       │
│    Proxy)       │    └─────────────────┘    └─────────────────┘
└─────────────────┘
```

## 📋 Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Node.js 18+
- Git

## 🛠️ Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/fs-reconciliation-agents.git
cd fs-reconciliation-agents
```

### 2. Environment Configuration
Create a `production.env` file with your configuration:
```bash
# Database Configuration
DATABASE_URL=postgresql://reconciliation_user:reconciliation_password@database:5432/reconciliation_db

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Security
SECRET_KEY=your_secret_key_here

# Redis Configuration
REDIS_URL=redis://redis:6379

# Feature Flags
DISABLE_EXCEPTION_LLM=false
DISABLE_MATCHING_LLM=false
DISABLE_INGESTION_LLM=true

# Logging
LOG_LEVEL=INFO

# CORS Settings
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
ALLOWED_HOSTS=*
```

### 3. Start the Application
```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### 4. Database Setup
```bash
# Run database migrations
docker exec fs-reconciliation-api alembic upgrade head

# Initialize database (if needed)
docker exec fs-reconciliation-db psql -U reconciliation_user -d reconciliation_db -f /app/init-database.sql
```

## 🚀 Usage

### Accessing the Application
- **Web Interface**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Key Features

#### 1. Data Upload
- Navigate to the Data Upload page
- Upload CSV files containing transaction data
- System automatically processes and normalizes data
- View processing status and results

#### 2. Exception Management
- View detected reconciliation exceptions
- Analyze AI-powered insights and recommendations
- Execute or review suggested workflows
- Track exception resolution progress

#### 3. Database Management
- Access comprehensive database management interface
- View, edit, and delete records across all tables
- Use advanced filtering and search capabilities
- Export data for external analysis
- Perform bulk operations on multiple records

#### 4. Governance & Monitoring
- Monitor system logs and performance metrics
- Review audit trail for compliance
- Track user activities and system usage
- Access detailed analytics and reporting

## 📊 Database Schema

### Core Tables
- **transactions**: Main transaction data
- **reconciliation_exceptions**: Detected breaks and exceptions
- **transaction_matches**: Matching results between transactions
- **system_logs**: Application logs and system events
- **audit_trail**: Comprehensive audit records

### Key Relationships
- Transactions can have multiple exceptions
- Transactions can be matched with other transactions
- All activities are logged in the audit trail
- System events are captured in system logs

## 🔧 Development

### Project Structure
```
fs-reconciliation-agents/
├── src/
│   ├── api/                 # FastAPI backend
│   ├── core/               # Core business logic
│   │   ├── agents/         # LangGraph agents
│   │   ├── models/         # Data models
│   │   ├── services/       # Business services
│   │   └── utils/          # Utilities
│   └── ui/                 # React frontend
├── docker/                 # Docker configurations
├── config/                 # Configuration files
├── data/                   # Data files
├── docs/                   # Documentation
├── scripts/                # Utility scripts
└── tests/                  # Test files
```

### Running in Development Mode
```bash
# Backend development
cd src/api
pip install -r requirements.txt
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Frontend development
cd src/ui
npm install
npm start
```

### Testing
```bash
# Run backend tests
docker exec fs-reconciliation-api python -m pytest

# Run frontend tests
docker exec fs-reconciliation-ui npm test
```

## 🔒 Security

### Authentication
- JWT-based authentication
- Role-based access control
- Secure session management

### Data Protection
- All sensitive data encrypted at rest
- Secure API endpoints with authentication
- Comprehensive audit logging
- Input validation and sanitization

## 📈 Monitoring & Observability

### Metrics
- Transaction processing rates
- Exception detection accuracy
- System performance metrics
- User activity tracking

### Logging
- Structured logging with different levels
- Centralized log management
- Error tracking and alerting
- Performance monitoring

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 for Python code
- Use TypeScript for frontend development
- Write comprehensive tests
- Update documentation for new features
- Follow conventional commit messages

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Troubleshooting
- Check the logs: `docker-compose logs -f [service-name]`
- Verify environment variables are set correctly
- Ensure all services are running: `docker-compose ps`
- Check database connectivity: `docker exec fs-reconciliation-db psql -U reconciliation_user -d reconciliation_db -c "\dt"`

### Common Issues
1. **Database connection errors**: Verify DATABASE_URL in production.env
2. **API not responding**: Check if all services are running
3. **UI not loading**: Verify the UI service is running on port 3000
4. **AI analysis not working**: Check OPENAI_API_KEY configuration

### Getting Help
- Create an issue on GitHub
- Check the documentation in the `/docs` folder
- Review the API documentation at `/docs` endpoint

## 🗺️ Roadmap

### Upcoming Features
- [ ] Advanced machine learning models for better matching
- [ ] Real-time notifications and alerts
- [ ] Mobile application
- [ ] Advanced reporting and analytics
- [ ] Integration with additional data sources
- [ ] Enhanced workflow automation
- [ ] Multi-tenant support
- [ ] Advanced security features

### Version History
- **v1.0.0**: Initial release with core reconciliation features
- **v1.1.0**: Enhanced database management and governance
- **v1.2.0**: Advanced AI analysis and workflow automation

---

**Built with ❤️ using modern technologies for reliable financial reconciliation**
