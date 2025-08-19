"""
Pytest configuration and fixtures for FS Reconciliation Agents testing.

This module provides:
- Database testing fixtures
- API client fixtures
- Authentication fixtures
- Mock services
- Test data generators
"""

import pytest
import asyncio
import tempfile
import os
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.api.main import app
from src.core.services.data_services.database import get_db_session
from src.core.utils.security_utils.authentication import create_access_token
from src.core.services.caching.redis_cache import RedisCacheService, CacheConfig


# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_password@localhost:5432/test_reconciliation_db"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        pool_pre_ping=True
    )
    yield engine
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def test_client() -> Generator[TestClient, None, None]:
    """Create test client for API testing."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def mock_cache_service():
    """Create mock cache service for testing."""
    mock_cache = AsyncMock(spec=RedisCacheService)
    mock_cache.get.return_value = None
    mock_cache.set.return_value = True
    mock_cache.delete.return_value = True
    mock_cache.exists.return_value = False
    mock_cache.clear_pattern.return_value = 0
    return mock_cache


@pytest.fixture
def test_user():
    """Create test user data."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123",
        "role": "analyst"
    }


@pytest.fixture
def test_token(test_user):
    """Create test JWT token."""
    return create_access_token(
        data={"sub": test_user["username"], "role": test_user["role"]}
    )


@pytest.fixture
def authenticated_client(test_client, test_token):
    """Create authenticated test client."""
    test_client.headers.update({"Authorization": f"Bearer {test_token}"})
    return test_client


@pytest.fixture
def sample_transaction_data():
    """Generate sample transaction data for testing."""
    return {
        "id": "TXN001",
        "security_id": "AAPL",
        "trade_date": "2024-01-15",
        "settlement_date": "2024-01-17",
        "amount": 100000.00,
        "quantity": 1000,
        "fx_rate": 1.0,
        "market_price": 100.00,
        "data_source": "source_a",
        "confidence_score": 0.95
    }


@pytest.fixture
def sample_exception_data():
    """Generate sample exception data for testing."""
    return {
        "id": "EXC001",
        "break_type": "market_price_break",
        "severity": "high",
        "status": "open",
        "description": "Market price mismatch detected",
        "break_amount": 500.00,
        "assigned_to": "testuser",
        "priority": "high"
    }


@pytest.fixture
def mock_ai_service():
    """Create mock AI service for testing."""
    mock_ai = AsyncMock()
    mock_ai.predict_break_probability.return_value = [
        {
            "transaction_id": "TXN001",
            "break_probability": 0.75,
            "confidence": 0.85,
            "risk_level": "high",
            "recommended_actions": ["Manual review required"]
        }
    ]
    mock_ai.detect_anomalies.return_value = [
        {
            "transaction_id": "TXN001",
            "is_anomaly": True,
            "anomaly_score": -0.8,
            "anomaly_type": "high_value_transaction",
            "severity": "high"
        }
    ]
    return mock_ai


@pytest.fixture
def mock_langgraph_agent():
    """Create mock LangGraph agent for testing."""
    mock_agent = AsyncMock()
    mock_agent.run.return_value = {
        "status": "completed",
        "result": "Reconciliation completed successfully",
        "exceptions_found": 2,
        "processing_time": 1.5
    }
    return mock_agent


@pytest.fixture
def temp_file():
    """Create temporary file for testing file uploads."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("id,security_id,trade_date,amount\nTXN001,AAPL,2024-01-15,100000.00\n")
        temp_file_path = f.name
    
    yield temp_file_path
    
    # Cleanup
    if os.path.exists(temp_file_path):
        os.unlink(temp_file_path)


@pytest.fixture
def mock_redis():
    """Create mock Redis connection for testing."""
    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.delete.return_value = 1
    mock_redis.exists.return_value = False
    return mock_redis


# Test data generators
class TestDataGenerator:
    """Generate test data for various scenarios."""
    
    @staticmethod
    def generate_transactions(count: int = 10):
        """Generate sample transaction data."""
        transactions = []
        for i in range(count):
            transaction = {
                "id": f"TXN{i:03d}",
                "security_id": f"SEC{i % 5}",
                "trade_date": "2024-01-15",
                "settlement_date": "2024-01-17",
                "amount": 10000.00 + (i * 1000),
                "quantity": 100 + (i * 10),
                "fx_rate": 1.0,
                "market_price": 100.00 + (i * 0.5),
                "data_source": "source_a" if i % 2 == 0 else "source_b",
                "confidence_score": 0.9 - (i * 0.01)
            }
            transactions.append(transaction)
        return transactions
    
    @staticmethod
    def generate_exceptions(count: int = 5):
        """Generate sample exception data."""
        break_types = ["market_price_break", "security_id_break", "fx_rate_break"]
        severities = ["low", "medium", "high"]
        statuses = ["open", "in_progress", "resolved"]
        
        exceptions = []
        for i in range(count):
            exception = {
                "id": f"EXC{i:03d}",
                "break_type": break_types[i % len(break_types)],
                "severity": severities[i % len(severities)],
                "status": statuses[i % len(statuses)],
                "description": f"Test exception {i}",
                "break_amount": 100.00 + (i * 50),
                "assigned_to": f"user{i % 3}",
                "priority": "high" if i % 3 == 0 else "medium"
            }
            exceptions.append(exception)
        return exceptions


@pytest.fixture
def test_data_generator():
    """Provide test data generator."""
    return TestDataGenerator


# Performance testing fixtures
@pytest.fixture
def performance_test_data():
    """Generate large dataset for performance testing."""
    return {
        "transactions": TestDataGenerator.generate_transactions(1000),
        "exceptions": TestDataGenerator.generate_exceptions(100),
        "users": [
            {"username": f"user{i}", "email": f"user{i}@example.com"}
            for i in range(10)
        ]
    }


# Security testing fixtures
@pytest.fixture
def malicious_inputs():
    """Provide malicious inputs for security testing."""
    return {
        "sql_injection": [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "'; INSERT INTO users VALUES ('hacker', 'password'); --"
        ],
        "xss": [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>"
        ],
        "path_traversal": [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd"
        ],
        "large_payloads": [
            "A" * 1000000,  # 1MB payload
            "A" * 10000000,  # 10MB payload
        ]
    }


# Error testing fixtures
@pytest.fixture
def error_scenarios():
    """Provide error scenarios for testing."""
    return {
        "database_connection_error": "Database connection failed",
        "cache_connection_error": "Redis connection failed",
        "file_upload_error": "File upload failed",
        "authentication_error": "Invalid credentials",
        "authorization_error": "Insufficient permissions",
        "validation_error": "Invalid input data",
        "processing_error": "Data processing failed"
    }


# Configuration for different test environments
@pytest.fixture(scope="session")
def test_config():
    """Test configuration."""
    return {
        "database": {
            "url": TEST_DATABASE_URL,
            "echo": False
        },
        "cache": {
            "url": "redis://localhost:6379/1",
            "ttl": 300
        },
        "api": {
            "base_url": "http://localhost:8000",
            "timeout": 30
        },
        "security": {
            "secret_key": "test_secret_key_for_testing_only",
            "algorithm": "HS256",
            "access_token_expire_minutes": 30
        }
    }


# Cleanup fixtures
@pytest.fixture(autouse=True)
async def cleanup_test_data(test_session):
    """Clean up test data after each test."""
    yield
    # Rollback any changes
    await test_session.rollback()


@pytest.fixture(scope="session", autouse=True)
async def setup_test_database(test_engine):
    """Set up test database schema."""
    # Create tables
    from src.core.models.data_models.transaction import Base
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Clean up
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
