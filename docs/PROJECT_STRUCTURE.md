# FS Reconciliation Agents - Project Structure

## Overview

This document provides a detailed overview of the project structure for the FS Reconciliation Agents application. The structure is designed to support a microservices architecture with Docker containerization, following best practices for scalability, maintainability, and deployment.

## Root Directory Structure

```
FS Reconciliation Agents/
├── BRD.md                           # Business Requirements Document
├── README.md                        # Project overview and quick start guide
├── requirements.txt                  # Python dependencies
├── docker-compose.yml               # Main Docker Compose configuration
├── .env.example                     # Environment variables template
├── .gitignore                       # Git ignore rules
├── Makefile                         # Development and deployment commands
├── setup.py                         # Python package setup
├── pyproject.toml                   # Python project configuration
│
├── src/                             # Source code
│   ├── __init__.py
│   ├── api/                         # API service
│   │   └── __init__.py
│   ├── core/                        # Core application logic
│   │   ├── __init__.py
│   │   ├── agents/                  # LangGraph agents
│   │   │   ├── __init__.py
│   │   │   ├── data_ingestion/      # Data ingestion agent
│   │   │   ├── normalization/       # Data normalization agent
│   │   │   ├── matching/            # Matching engine agent
│   │   │   ├── exception_identification/ # Exception detection agent
│   │   │   ├── resolution/          # Resolution agent
│   │   │   ├── reporting/           # Reporting agent
│   │   │   └── human_in_loop/       # Human-in-the-loop agent
│   │   ├── models/                  # Data models
│   │   │   ├── __init__.py
│   │   │   ├── data_models/         # Core data models
│   │   │   ├── break_types/         # Break type definitions
│   │   │   └── audit_models/        # Audit trail models
│   │   ├── services/                # Business services
│   │   │   ├── __init__.py
│   │   │   ├── data_services/       # Data processing services
│   │   │   ├── calculation_services/ # Financial calculation services
│   │   │   └── notification_services/ # Notification services
│   │   └── utils/                   # Utility functions
│   │       ├── __init__.py
│   │       ├── data_utils/          # Data processing utilities
│   │       ├── validation_utils/    # Validation utilities
│   │       └── security_utils/      # Security utilities
│   └── ui/                          # User interface
│       ├── __init__.py
│       ├── components/              # React components
│       │   ├── __init__.py
│       │   ├── dashboard/           # Dashboard components
│       │   ├── exceptions/          # Exception management components
│       │   ├── reports/             # Reporting components
│       │   └── configuration/       # Configuration components
│       ├── pages/                   # Page components
│       │   ├── __init__.py
│       │   ├── dashboard/           # Dashboard pages
│       │   ├── exceptions/          # Exception pages
│       │   ├── reports/             # Report pages
│       │   └── settings/            # Settings pages
│       ├── styles/                  # Styling
│       │   ├── __init__.py
│       │   ├── components/          # Component styles
│       │   ├── layouts/             # Layout styles
│       │   └── themes/              # Theme definitions
│       └── utils/                   # UI utilities
│           ├── __init__.py
│           ├── api_utils/           # API interaction utilities
│           ├── form_utils/          # Form handling utilities
│           └── chart_utils/         # Chart and visualization utilities
│
├── docker/                          # Docker configurations
│   ├── langgraph-agent/             # LangGraph agent service
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── api-service/                 # API service
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── ui-service/                  # UI service
│       ├── Dockerfile
│       └── nginx.conf
│
├── config/                          # Configuration files
│   ├── config.yaml                  # Main application configuration
│   ├── logging.yaml                 # Logging configuration
│   └── database.yaml                # Database configuration
│
├── tests/                           # Test suites
│   ├── __init__.py
│   ├── unit/                        # Unit tests
│   ├── integration/                 # Integration tests
│   └── e2e/                         # End-to-end tests
│
├── data/                            # Data storage
│   ├── __init__.py
│   ├── raw/                         # Raw data files
│   ├── processed/                   # Processed data files
│   └── exports/                     # Export files
│
├── logs/                            # Application logs
│   └── __init__.py
│
├── scripts/                         # Utility scripts
│   └── __init__.py
│
├── deployment/                      # Deployment configurations
│   ├── __init__.py
│   ├── local/                       # Local deployment
│   └── production/                  # Production deployment
│
└── docs/                            # Documentation
    ├── BUILD_PLAN.md                # Detailed build plan
    └── PROJECT_STRUCTURE.md         # This file
```

## Key Components

### 1. Source Code (`src/`)

#### API Service (`src/api/`)
- RESTful API endpoints
- Request/response handling
- Authentication and authorization
- API documentation

#### Core Logic (`src/core/`)
- **Agents**: LangGraph workflow agents for each reconciliation step
- **Models**: Data models and schemas
- **Services**: Business logic and external integrations
- **Utils**: Shared utility functions

#### UI (`src/ui/`)
- React-based user interface
- Deloitte brand compliance
- Component-based architecture
- Responsive design

### 2. Docker Configuration (`docker/`)

#### LangGraph Agent Service
- Core AI workflow engine
- LangGraph framework implementation
- OpenAI integration

#### API Service
- FastAPI application
- Database integration
- Authentication middleware

#### UI Service
- React application
- Nginx web server
- Static file serving

### 3. Configuration (`config/`)

- Application settings
- Database configuration
- Logging configuration
- Environment-specific settings

### 4. Testing (`tests/`)

- Unit tests for individual components
- Integration tests for workflows
- End-to-end tests for complete scenarios
- Performance and security testing

### 5. Data Management (`data/`)

- Raw data storage
- Processed data files
- Export functionality
- Data lineage tracking

### 6. Deployment (`deployment/`)

- Local development setup
- Production deployment configuration
- Environment-specific Docker Compose files

## Architecture Principles

### 1. Microservices Architecture
- Each service is containerized independently
- Services communicate via APIs
- Scalable and maintainable design

### 2. Separation of Concerns
- Clear separation between UI, API, and core logic
- Modular agent design
- Reusable components and utilities

### 3. Security First
- Environment variable management
- Secure API key handling
- Database security
- Audit trail implementation

### 4. Scalability
- Horizontal scaling capabilities
- Load balancing support
- Caching strategies
- Performance monitoring

### 5. Maintainability
- Comprehensive testing
- Code quality tools
- Documentation
- Version control

## Development Workflow

### 1. Local Development
```bash
# Set up environment
make setup-dev

# Build and start services
make build && make up

# View logs
make logs

# Run tests
make test
```

### 2. Code Quality
```bash
# Format code
make format

# Run linting
make lint

# Type checking
make type-check
```

### 3. Database Management
```bash
# Run migrations
make db-migrate

# Reset database (development only)
make db-reset
```

### 4. Deployment
```bash
# Local deployment
make deploy-local

# Production deployment
make deploy-prod
```

## File Naming Conventions

### Python Files
- Use snake_case for file and function names
- Use PascalCase for class names
- Use UPPER_CASE for constants

### JavaScript/TypeScript Files
- Use camelCase for variables and functions
- Use PascalCase for components and classes
- Use kebab-case for file names

### Configuration Files
- Use YAML for configuration files
- Use .env for environment variables
- Use .json for static data

## Security Considerations

### 1. Environment Variables
- Never commit sensitive data to version control
- Use .env.example for templates
- Implement proper secret management

### 2. Database Security
- Use connection pooling
- Implement proper authentication
- Regular security updates

### 3. API Security
- JWT token authentication
- Rate limiting
- Input validation
- CORS configuration

### 4. Container Security
- Non-root users in containers
- Minimal base images
- Regular security scans
- Network isolation

## Monitoring and Logging

### 1. Application Logging
- Structured logging with structlog
- Log levels (DEBUG, INFO, WARNING, ERROR)
- Centralized log management

### 2. Health Checks
- Service health endpoints
- Database connectivity checks
- External service monitoring

### 3. Performance Monitoring
- API response times
- Database query performance
- Resource utilization
- Error rates

## Future Enhancements

### 1. Scalability
- Kubernetes deployment
- Auto-scaling capabilities
- Multi-region deployment

### 2. Advanced Features
- Machine learning model training
- Advanced analytics
- Real-time streaming
- Mobile application

### 3. Integration
- Additional data sources
- Third-party integrations
- API marketplace
- Webhook support

This structure provides a solid foundation for building a robust, scalable, and maintainable agentic bank reconciliation application that meets all the requirements outlined in the BRD. 