"""
Authentication utilities for FS Reconciliation Agents.

This module provides authentication and authorization functionality
including JWT token management and user session handling.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from src.core.services.data_services.config_service import get_secret_key, get_jwt_secret_key

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = get_secret_key()
JWT_SECRET_KEY = get_jwt_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Security scheme (allow missing credentials when anonymous access is enabled)
security = HTTPBearer(auto_error=False)


class Token(BaseModel):
    """Token model."""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Token data model."""
    username: Optional[str] = None


class User(BaseModel):
    """User model."""
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None


class UserInDB(User):
    """User in database model."""
    hashed_password: str


# Mock user database (replace with actual database)
fake_users_db = {
    "admin": {
        "username": "admin",
        "full_name": "Administrator",
        "email": "admin@fsreconciliation.com",
        "hashed_password": pwd_context.hash("admin123"),
        "disabled": False,
    },
    "user1": {
        "username": "user1",
        "full_name": "John Doe",
        "email": "john.doe@fsreconciliation.com",
        "hashed_password": pwd_context.hash("user123"),
        "disabled": False,
    }
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def get_user(db: Dict[str, Any], username: str) -> Optional[UserInDB]:
    """Get user from database."""
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)
    return None


def authenticate_user(fake_db: Dict[str, Any], username: str, password: str) -> Optional[UserInDB]:
    """Authenticate a user."""
    user = get_user(fake_db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create an access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)
    return str(encoded_jwt)


def _allow_anonymous() -> bool:
    return os.getenv("ALLOW_ANONYMOUS", "false").lower() in ("1", "true", "yes")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current user from token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Allow anonymous user when enabled and no credentials provided
    if credentials is None and _allow_anonymous():
        return User(username="anonymous", full_name="Anonymous User", disabled=False)
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(fake_users_db, username=token_data.username)
    if user is None:
        # If token is valid but user is not in mock DB and anonymous is allowed, return anonymous
        if _allow_anonymous():
            return User(username=username or "anonymous")
        raise credentials_exception
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user."""
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def create_user_access_token(username: str) -> str:
    """Create access token for user."""
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": username}, expires_delta=access_token_expires
    )
    return access_token


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def get_user_from_token(token: str) -> Optional[str]:
    """Get username from token."""
    payload = verify_token(token)
    if payload:
        return payload.get("sub")
    return None


def is_token_expired(token: str) -> bool:
    """Check if token is expired."""
    payload = verify_token(token)
    if not payload:
        return True
    
    exp = payload.get("exp")
    if not exp:
        return True
    
    try:
        exp_datetime = datetime.fromtimestamp(exp)
        return datetime.utcnow() > exp_datetime
    except (ValueError, TypeError):
        return True


def refresh_token(token: str) -> Optional[str]:
    """Refresh an access token."""
    payload = verify_token(token)
    if not payload:
        return None
    
    username = payload.get("sub")
    if not username:
        return None
    
    # Create new token
    return create_user_access_token(username)


# Role-based access control
class Role:
    """Role definitions."""
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


def has_role(user: User, role: str) -> bool:
    """Check if user has a specific role."""
    # Mock role checking - replace with actual role management
    if user.username == "admin":
        return True
    elif role == Role.USER and user.username in ["user1", "admin"]:
        return True
    elif role == Role.VIEWER:
        return True
    return False


def require_role(role: str):
    """Decorator to require a specific role."""
    def role_checker(current_user: User = Depends(get_current_active_user)):
        if not has_role(current_user, role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    return role_checker


# Session management
class SessionManager:
    """Session manager for user sessions."""
    
    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
    
    def create_session(self, user: User, token: str) -> str:
        """Create a new user session."""
        session_id = f"{user.username}_{datetime.utcnow().timestamp()}"
        self.active_sessions[session_id] = {
            "user": user,
            "token": token,
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow()
        }
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID."""
        session = self.active_sessions.get(session_id)
        if session:
            session["last_activity"] = datetime.utcnow()
        return session
    
    def remove_session(self, session_id: str) -> bool:
        """Remove a session."""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            return True
        return False
    
    def cleanup_expired_sessions(self, max_age_hours: int = 24) -> int:
        """Clean up expired sessions."""
        now = datetime.utcnow()
        expired_sessions = []
        
        for session_id, session in self.active_sessions.items():
            age = now - session["created_at"]
            if age.total_seconds() > max_age_hours * 3600:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.active_sessions[session_id]
        
        return len(expired_sessions)


# Global session manager
session_manager = SessionManager()


# Security utilities
def hash_sensitive_data(data: str) -> str:
    """Hash sensitive data for logging."""
    import hashlib
    return hashlib.sha256(data.encode()).hexdigest()[:8]


def mask_sensitive_data(data: str, mask_char: str = "*") -> str:
    """Mask sensitive data for display."""
    if len(data) <= 4:
        return mask_char * len(data)
    return data[:2] + mask_char * (len(data) - 4) + data[-2:]


def validate_password_strength(password: str) -> Dict[str, Any]:
    """Validate password strength."""
    errors = []
    warnings = []
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    
    if not any(c.isupper() for c in password):
        warnings.append("Password should contain uppercase letters")
    
    if not any(c.islower() for c in password):
        warnings.append("Password should contain lowercase letters")
    
    if not any(c.isdigit() for c in password):
        warnings.append("Password should contain numbers")
    
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        warnings.append("Password should contain special characters")
    
    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "score": max(0, 10 - len(errors) * 2 - len(warnings))
    } 