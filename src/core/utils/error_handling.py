"""
Comprehensive error handling for FS Reconciliation Agents.

This module provides:
- Custom exception classes
- Error response formatting
- Error logging and monitoring
- Retry mechanisms
- Circuit breaker pattern
- Error recovery strategies
"""

import traceback
import logging
import asyncio
from typing import Dict, Any, Optional, Callable, Type, Union
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
import json

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories."""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATABASE = "database"
    NETWORK = "network"
    EXTERNAL_SERVICE = "external_service"
    BUSINESS_LOGIC = "business_logic"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class ReconciliationError(Exception):
    """Base exception for reconciliation system."""
    
    def __init__(
        self,
        message: str,
        error_code: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        retryable: bool = False,
        max_retries: int = 3
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.category = category
        self.severity = severity
        self.details = details or {}
        self.retryable = retryable
        self.max_retries = max_retries
        self.timestamp = datetime.now()
        self.traceback = traceback.format_exc()


class ValidationError(ReconciliationError):
    """Validation error."""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            details={"field": field, "value": value},
            retryable=False
        )


class AuthenticationError(ReconciliationError):
    """Authentication error."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            retryable=False
        )


class AuthorizationError(ReconciliationError):
    """Authorization error."""
    
    def __init__(self, message: str = "Access denied"):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            category=ErrorCategory.AUTHORIZATION,
            severity=ErrorSeverity.HIGH,
            retryable=False
        )


class DatabaseError(ReconciliationError):
    """Database error."""
    
    def __init__(self, message: str, operation: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            details={"operation": operation},
            retryable=True,
            max_retries=5
        )


class NetworkError(ReconciliationError):
    """Network error."""
    
    def __init__(self, message: str, endpoint: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="NETWORK_ERROR",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            details={"endpoint": endpoint},
            retryable=True,
            max_retries=3
        )


class ExternalServiceError(ReconciliationError):
    """External service error."""
    
    def __init__(self, message: str, service: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR",
            category=ErrorCategory.EXTERNAL_SERVICE,
            severity=ErrorSeverity.MEDIUM,
            details={"service": service},
            retryable=True,
            max_retries=3
        )


class BusinessLogicError(ReconciliationError):
    """Business logic error."""
    
    def __init__(self, message: str, rule: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="BUSINESS_LOGIC_ERROR",
            category=ErrorCategory.BUSINESS_LOGIC,
            severity=ErrorSeverity.MEDIUM,
            details={"rule": rule},
            retryable=False
        )


class SystemError(ReconciliationError):
    """System error."""
    
    def __init__(self, message: str, component: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="SYSTEM_ERROR",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.CRITICAL,
            details={"component": component},
            retryable=True,
            max_retries=2
        )


class ErrorHandler:
    """Centralized error handler."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_counts = {}
        self.error_thresholds = {
            ErrorSeverity.LOW: 100,
            ErrorSeverity.MEDIUM: 50,
            ErrorSeverity.HIGH: 20,
            ErrorSeverity.CRITICAL: 5
        }
    
    def handle_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle and format error response."""
        if isinstance(error, ReconciliationError):
            return self._handle_reconciliation_error(error, context)
        else:
            return self._handle_generic_error(error, context)
    
    def _handle_reconciliation_error(self, error: ReconciliationError, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle reconciliation-specific errors."""
        # Log error
        self._log_error(error, context)
        
        # Update error counts
        self._update_error_counts(error)
        
        # Check for error thresholds
        self._check_error_thresholds(error)
        
        # Format response
        response = {
            "error": {
                "type": error.category.value,
                "code": error.error_code,
                "message": error.message,
                "severity": error.severity.value,
                "timestamp": error.timestamp.isoformat(),
                "retryable": error.retryable,
                "details": error.details
            },
            "suggestions": self._get_error_suggestions(error),
            "request_id": context.get("request_id") if context else None
        }
        
        return response
    
    def _handle_generic_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle generic errors."""
        # Log error
        self._log_error(error, context)
        
        # Format response
        response = {
            "error": {
                "type": "unknown",
                "code": "UNKNOWN_ERROR",
                "message": str(error),
                "severity": ErrorSeverity.MEDIUM.value,
                "timestamp": datetime.now().isoformat(),
                "retryable": False,
                "details": {}
            },
            "suggestions": ["Contact system administrator"],
            "request_id": context.get("request_id") if context else None
        }
        
        return response
    
    def _log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None):
        """Log error with context."""
        log_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.now().isoformat(),
            "context": context or {}
        }
        
        if isinstance(error, ReconciliationError):
            log_data.update({
                "error_code": error.error_code,
                "category": error.category.value,
                "severity": error.severity.value,
                "retryable": error.retryable,
                "details": error.details
            })
        
        if hasattr(error, 'traceback'):
            log_data["traceback"] = error.traceback
        
        self.logger.error(f"Error occurred: {json.dumps(log_data, indent=2)}")
    
    def _update_error_counts(self, error: ReconciliationError):
        """Update error count tracking."""
        key = f"{error.category.value}_{error.error_code}"
        self.error_counts[key] = self.error_counts.get(key, 0) + 1
    
    def _check_error_thresholds(self, error: ReconciliationError):
        """Check if error thresholds are exceeded."""
        threshold = self.error_thresholds.get(error.severity, 100)
        key = f"{error.category.value}_{error.error_code}"
        count = self.error_counts.get(key, 0)
        
        if count >= threshold:
            self.logger.critical(f"Error threshold exceeded for {key}: {count} errors")
            # Could trigger alerts, circuit breaker, etc.
    
    def _get_error_suggestions(self, error: ReconciliationError) -> list:
        """Get suggestions for error resolution."""
        suggestions = []
        
        if error.category == ErrorCategory.VALIDATION:
            suggestions.extend([
                "Check input data format",
                "Verify required fields are provided",
                "Ensure data types are correct"
            ])
        elif error.category == ErrorCategory.AUTHENTICATION:
            suggestions.extend([
                "Verify credentials",
                "Check token expiration",
                "Ensure proper authentication headers"
            ])
        elif error.category == ErrorCategory.DATABASE:
            suggestions.extend([
                "Check database connectivity",
                "Verify database permissions",
                "Review database logs"
            ])
        elif error.category == ErrorCategory.NETWORK:
            suggestions.extend([
                "Check network connectivity",
                "Verify endpoint availability",
                "Review firewall settings"
            ])
        elif error.category == ErrorCategory.EXTERNAL_SERVICE:
            suggestions.extend([
                "Check external service status",
                "Verify API credentials",
                "Review rate limits"
            ])
        
        if error.retryable:
            suggestions.append("This operation can be retried")
        
        return suggestions


class RetryHandler:
    """Retry mechanism for failed operations."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    async def retry_operation(
        self,
        operation: Callable,
        *args,
        retryable_exceptions: tuple = (Exception,),
        **kwargs
    ) -> Any:
        """Retry an operation with exponential backoff."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(operation):
                    return await operation(*args, **kwargs)
                else:
                    return operation(*args, **kwargs)
            
            except retryable_exceptions as e:
                last_exception = e
                
                if attempt == self.max_retries:
                    raise e
                
                # Calculate delay with exponential backoff
                delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                
                # Add jitter to prevent thundering herd
                jitter = delay * 0.1 * (1 - 2 * (hash(str(attempt)) % 100) / 100)
                delay += jitter
                
                logging.warning(f"Operation failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}. Retrying in {delay:.2f}s")
                await asyncio.sleep(delay)
        
        raise last_exception


class CircuitBreaker:
    """Circuit breaker pattern implementation."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute operation with circuit breaker protection."""
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            if asyncio.iscoroutinefunction(operation):
                result = await operation(*args, **kwargs)
            else:
                result = operation(*args, **kwargs)
            
            self._on_success()
            return result
        
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        """Handle successful operation."""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        """Handle failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset."""
        if self.last_failure_time is None:
            return True
        
        return (datetime.now() - self.last_failure_time).total_seconds() >= self.recovery_timeout


class ErrorRecovery:
    """Error recovery strategies."""
    
    @staticmethod
    async def recover_database_connection(database_service, max_attempts: int = 3):
        """Recover database connection."""
        for attempt in range(max_attempts):
            try:
                await database_service.test_connection()
                logging.info("Database connection recovered")
                return True
            except Exception as e:
                logging.warning(f"Database recovery attempt {attempt + 1} failed: {e}")
                if attempt < max_attempts - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        logging.error("Database connection recovery failed")
        return False
    
    @staticmethod
    async def recover_cache_connection(cache_service, max_attempts: int = 3):
        """Recover cache connection."""
        for attempt in range(max_attempts):
            try:
                await cache_service.ping()
                logging.info("Cache connection recovered")
                return True
            except Exception as e:
                logging.warning(f"Cache recovery attempt {attempt + 1} failed: {e}")
                if attempt < max_attempts - 1:
                    await asyncio.sleep(2 ** attempt)
        
        logging.error("Cache connection recovery failed")
        return False
    
    @staticmethod
    async def recover_external_service(service_client, max_attempts: int = 3):
        """Recover external service connection."""
        for attempt in range(max_attempts):
            try:
                await service_client.health_check()
                logging.info("External service connection recovered")
                return True
            except Exception as e:
                logging.warning(f"External service recovery attempt {attempt + 1} failed: {e}")
                if attempt < max_attempts - 1:
                    await asyncio.sleep(2 ** attempt)
        
        logging.error("External service connection recovery failed")
        return False


def handle_errors(error_handler: ErrorHandler = None):
    """Decorator for error handling."""
    if error_handler is None:
        error_handler = ErrorHandler()
    
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_response = error_handler.handle_error(e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=error_response
                )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_response = error_handler.handle_error(e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=error_response
                )
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def retry_on_failure(max_retries: int = 3, retryable_exceptions: tuple = (Exception,)):
    """Decorator for retry logic."""
    def decorator(func):
        retry_handler = RetryHandler(max_retries=max_retries)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await retry_handler.retry_operation(
                func, *args, retryable_exceptions=retryable_exceptions, **kwargs
            )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return retry_handler.retry_operation(
                func, *args, retryable_exceptions=retryable_exceptions, **kwargs
            )
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def circuit_breaker(failure_threshold: int = 5, recovery_timeout: float = 60.0):
    """Decorator for circuit breaker pattern."""
    def decorator(func):
        breaker = CircuitBreaker(failure_threshold=failure_threshold, recovery_timeout=recovery_timeout)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await breaker.call(func, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Global error handler instance
error_handler = ErrorHandler()
