"""
Security middleware for FS Reconciliation Agents.

This module provides:
- Rate limiting
- Input validation and sanitization
- Security headers
- CORS configuration
- Request size limits
- IP filtering
- Audit logging
"""

import re
import hashlib
import ipaddress
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from collections import defaultdict
import json

from fastapi import Request, Response, HTTPException, status
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from src.core.utils.audit_logger import AuditLogger


class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware for the application."""
    
    def __init__(
        self,
        app,
        rate_limit_requests: int = 100,
        rate_limit_window: int = 60,
        max_request_size: int = 10 * 1024 * 1024,  # 10MB
        allowed_ips: Optional[List[str]] = None,
        blocked_ips: Optional[List[str]] = None,
        enable_cors: bool = True,
        cors_origins: Optional[List[str]] = None,
        enable_security_headers: bool = True,
        enable_input_validation: bool = True,
        enable_audit_logging: bool = True
    ):
        super().__init__(app)
        self.rate_limit_requests = rate_limit_requests
        self.rate_limit_window = rate_limit_window
        self.max_request_size = max_request_size
        self.allowed_ips = allowed_ips or []
        self.blocked_ips = blocked_ips or []
        self.enable_cors = enable_cors
        self.cors_origins = cors_origins or ["*"]
        self.enable_security_headers = enable_security_headers
        self.enable_input_validation = enable_input_validation
        self.enable_audit_logging = enable_audit_logging
        
        # Rate limiting storage
        self.rate_limit_store = defaultdict(list)
        
        # Security patterns
        self.sql_injection_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
            r"(\b(OR|AND)\b\s+\d+\s*=\s*\d+)",
            r"(\b(OR|AND)\b\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?)",
            r"(--|\b(COMMENT|REM)\b)",
            r"(\b(WAITFOR|DELAY)\b)",
            r"(\b(BENCHMARK|SLEEP)\b)",
            r"(\b(LOAD_FILE|INTO\s+OUTFILE)\b)",
        ]
        
        self.xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>",
            r"<object[^>]*>",
            r"<embed[^>]*>",
            r"<form[^>]*>",
            r"<input[^>]*>",
            r"<textarea[^>]*>",
            r"<select[^>]*>",
            r"<link[^>]*>",
            r"<meta[^>]*>",
            r"<style[^>]*>",
        ]
        
        self.path_traversal_patterns = [
            r"\.\./",
            r"\.\.\\",
            r"\.\.%2f",
            r"\.\.%5c",
            r"\.\.%252f",
            r"\.\.%255c",
        ]
        
        # Compile patterns for performance
        self.sql_injection_regex = re.compile("|".join(self.sql_injection_patterns), re.IGNORECASE)
        self.xss_regex = re.compile("|".join(self.xss_patterns), re.IGNORECASE)
        self.path_traversal_regex = re.compile("|".join(self.path_traversal_patterns), re.IGNORECASE)
        
        # Audit logger
        self.audit_logger = AuditLogger()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through security middleware."""
        start_time = datetime.now()
        
        try:
            # 1. IP filtering
            await self._check_ip_filtering(request)
            
            # 2. Rate limiting
            await self._check_rate_limit(request)
            
            # 3. Request size validation
            await self._check_request_size(request)
            
            # 4. Input validation and sanitization
            if self.enable_input_validation:
                await self._validate_input(request)
            
            # 5. Process request
            response = await call_next(request)
            
            # 6. Add security headers
            if self.enable_security_headers:
                response = await self._add_security_headers(request, response)
            
            # 7. CORS headers
            if self.enable_cors:
                response = await self._add_cors_headers(request, response)
            
            # 8. Audit logging
            if self.enable_audit_logging:
                await self._log_audit_event(request, response, start_time)
            
            return response
            
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            # Log unexpected errors
            await self._log_security_event(request, "unexpected_error", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
    
    async def _check_ip_filtering(self, request: Request):
        """Check IP filtering rules."""
        client_ip = self._get_client_ip(request)
        
        # Check blocked IPs
        if client_ip in self.blocked_ips:
            await self._log_security_event(request, "blocked_ip", f"IP {client_ip} is blocked")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Check allowed IPs (if specified)
        if self.allowed_ips and client_ip not in self.allowed_ips:
            await self._log_security_event(request, "unauthorized_ip", f"IP {client_ip} not in allowed list")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    async def _check_rate_limit(self, request: Request):
        """Check rate limiting."""
        client_ip = self._get_client_ip(request)
        current_time = datetime.now()
        
        # Clean old entries
        self.rate_limit_store[client_ip] = [
            timestamp for timestamp in self.rate_limit_store[client_ip]
            if current_time - timestamp < timedelta(seconds=self.rate_limit_window)
        ]
        
        # Check if limit exceeded
        if len(self.rate_limit_store[client_ip]) >= self.rate_limit_requests:
            await self._log_security_event(request, "rate_limit_exceeded", f"IP {client_ip} exceeded rate limit")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )
        
        # Add current request
        self.rate_limit_store[client_ip].append(current_time)
    
    async def _check_request_size(self, request: Request):
        """Check request size limits."""
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_request_size:
            await self._log_security_event(request, "request_too_large", f"Request size {content_length} exceeds limit")
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Request too large"
            )
    
    async def _validate_input(self, request: Request):
        """Validate and sanitize input."""
        # Check URL parameters
        for param_name, param_value in request.query_params.items():
            if self._is_malicious_input(param_value):
                await self._log_security_event(request, "malicious_input", f"Malicious input in parameter {param_name}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid input detected"
                )
        
        # Check path parameters
        for param_name, param_value in request.path_params.items():
            if self._is_malicious_input(param_value):
                await self._log_security_event(request, "malicious_input", f"Malicious input in path parameter {param_name}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid input detected"
                )
        
        # Check request body for JSON requests
        if request.headers.get("content-type", "").startswith("application/json"):
            try:
                body = await request.body()
                if body:
                    body_str = body.decode("utf-8")
                    if self._is_malicious_input(body_str):
                        await self._log_security_event(request, "malicious_input", "Malicious input in request body")
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid input detected"
                        )
            except Exception:
                # If we can't read the body, continue
                pass
    
    def _is_malicious_input(self, input_str: str) -> bool:
        """Check if input contains malicious patterns."""
        if not isinstance(input_str, str):
            return False
        
        # Check for SQL injection
        if self.sql_injection_regex.search(input_str):
            return True
        
        # Check for XSS
        if self.xss_regex.search(input_str):
            return True
        
        # Check for path traversal
        if self.path_traversal_regex.search(input_str):
            return True
        
        return False
    
    async def _add_security_headers(self, request: Request, response: Response) -> Response:
        """Add security headers to response."""
        # Content Security Policy
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' https:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers["Content-Security-Policy"] = csp_policy
        
        # XSS Protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Content Type Options
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Frame Options
        response.headers["X-Frame-Options"] = "DENY"
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy
        permissions_policy = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )
        response.headers["Permissions-Policy"] = permissions_policy
        
        # HSTS (for HTTPS)
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Remove server information
        if "server" in response.headers:
            del response.headers["server"]
        
        return response
    
    async def _add_cors_headers(self, request: Request, response: Response) -> Response:
        """Add CORS headers to response."""
        origin = request.headers.get("origin")
        
        if origin and (origin in self.cors_origins or "*" in self.cors_origins):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Get the real client IP address."""
        # Check for forwarded headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        if request.client:
            return request.client.host
        
        return "unknown"
    
    async def _log_security_event(self, request: Request, event_type: str, details: str):
        """Log security events."""
        security_data = {
            "event_type": event_type,
            "details": details,
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent", ""),
            "method": request.method,
            "path": str(request.url.path),
            "timestamp": datetime.now().isoformat()
        }
        
        await self.audit_logger.log_security_event(security_data)
    
    async def _log_audit_event(self, request: Request, response: Response, start_time: datetime):
        """Log audit events."""
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        audit_data = {
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent", ""),
            "method": request.method,
            "path": str(request.url.path),
            "query_params": dict(request.query_params),
            "status_code": response.status_code,
            "duration": duration,
            "timestamp": start_time.isoformat(),
            "request_id": request.headers.get("x-request-id", "")
        }
        
        await self.audit_logger.log_audit_event(audit_data)


class InputSanitizer:
    """Input sanitization utilities."""
    
    @staticmethod
    def sanitize_string(input_str: str) -> str:
        """Sanitize string input."""
        if not isinstance(input_str, str):
            return str(input_str)
        
        # Remove null bytes
        input_str = input_str.replace("\x00", "")
        
        # Remove control characters except newlines and tabs
        input_str = "".join(char for char in input_str if ord(char) >= 32 or char in "\n\t")
        
        # Normalize whitespace
        input_str = " ".join(input_str.split())
        
        return input_str
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename."""
        if not isinstance(filename, str):
            return "unknown"
        
        # Remove path traversal
        filename = filename.replace("..", "").replace("/", "").replace("\\", "")
        
        # Remove dangerous characters
        dangerous_chars = "<>:\"|?*"
        for char in dangerous_chars:
            filename = filename.replace(char, "")
        
        # Limit length
        if len(filename) > 255:
            filename = filename[:255]
        
        return filename
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        if not isinstance(email, str):
            return False
        
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(email_pattern, email))
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format."""
        if not isinstance(url, str):
            return False
        
        url_pattern = r"^https?://[^\s/$.?#].[^\s]*$"
        return bool(re.match(url_pattern, url))


class PasswordValidator:
    """Password validation utilities."""
    
    @staticmethod
    def validate_password(password: str) -> Dict[str, Any]:
        """Validate password strength."""
        if not isinstance(password, str):
            return {"valid": False, "errors": ["Password must be a string"]}
        
        errors = []
        
        # Check length
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        
        if len(password) > 128:
            errors.append("Password must be less than 128 characters long")
        
        # Check for required character types
        if not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not re.search(r"\d", password):
            errors.append("Password must contain at least one digit")
        
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            errors.append("Password must contain at least one special character")
        
        # Check for common patterns
        common_patterns = [
            "password", "123456", "qwerty", "admin", "user",
            "letmein", "welcome", "monkey", "dragon", "master"
        ]
        
        if password.lower() in common_patterns:
            errors.append("Password cannot be a common password")
        
        # Check for sequential characters
        if re.search(r"(.)\1{2,}", password):
            errors.append("Password cannot contain repeated characters")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "strength": PasswordValidator._calculate_strength(password)
        }
    
    @staticmethod
    def _calculate_strength(password: str) -> str:
        """Calculate password strength."""
        score = 0
        
        # Length bonus
        score += min(len(password) * 4, 20)
        
        # Character variety bonus
        if re.search(r"[a-z]", password):
            score += 5
        if re.search(r"[A-Z]", password):
            score += 5
        if re.search(r"\d", password):
            score += 5
        if re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            score += 5
        
        # Deduct for common patterns
        if re.search(r"(.)\1{2,}", password):
            score -= 10
        
        if score < 20:
            return "weak"
        elif score < 40:
            return "medium"
        elif score < 60:
            return "strong"
        else:
            return "very_strong"


class TokenValidator:
    """Token validation utilities."""
    
    @staticmethod
    def validate_jwt_token(token: str) -> bool:
        """Basic JWT token format validation."""
        if not isinstance(token, str):
            return False
        
        # Check JWT format (header.payload.signature)
        parts = token.split(".")
        if len(parts) != 3:
            return False
        
        # Check if parts are base64 encoded
        try:
            import base64
            for part in parts:
                base64.b64decode(part + "==")  # Add padding
            return True
        except Exception:
            return False
    
    @staticmethod
    def generate_secure_token() -> str:
        """Generate a secure random token."""
        import secrets
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def hash_token(token: str) -> str:
        """Hash a token for storage."""
        return hashlib.sha256(token.encode()).hexdigest()
