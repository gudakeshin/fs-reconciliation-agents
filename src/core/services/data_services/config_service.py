"""
Configuration service for FS Reconciliation Agents.

This module provides centralized configuration management for the application,
loading settings from YAML files and environment variables.
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Global configuration cache
_config_cache: Optional[Dict[str, Any]] = None


def load_config() -> Dict[str, Any]:
    """Load configuration from YAML files and environment variables."""
    global _config_cache
    
    if _config_cache is not None:
        return _config_cache
    
    config = {}
    
    # Load main configuration
    config_path = Path("config/config.yaml")
    if config_path.exists():
        with open(config_path, 'r') as f:
            config.update(yaml.safe_load(f))
    
    # Load database configuration
    db_config_path = Path("config/database.yaml")
    if db_config_path.exists():
        with open(db_config_path, 'r') as f:
            config['database'] = yaml.safe_load(f)
    
    # Load logging configuration
    logging_config_path = Path("config/logging.yaml")
    if logging_config_path.exists():
        with open(logging_config_path, 'r') as f:
            config['logging'] = yaml.safe_load(f)
    
    # Load OpenAI configuration
    openai_config_path = Path("config/openai_config.yaml")
    if openai_config_path.exists():
        with open(openai_config_path, 'r') as f:
            config['openai'] = yaml.safe_load(f)
    
    # Replace environment variables
    config = _replace_env_vars(config)
    
    _config_cache = config
    return config


def _replace_env_vars(config: Dict[str, Any]) -> Dict[str, Any]:
    """Replace environment variable placeholders in configuration."""
    if isinstance(config, dict):
        return {k: _replace_env_vars(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [_replace_env_vars(v) for v in config]
    elif isinstance(config, str) and config.startswith("${") and config.endswith("}"):
        env_var = config[2:-1]
        return os.getenv(env_var, "")
    else:
        return config


def get_config() -> Dict[str, Any]:
    """Get the application configuration."""
    return load_config()


def get_openai_config() -> Dict[str, Any]:
    """Get OpenAI configuration."""
    config = get_config()
    return config.get('openai', {})


def get_agent_config(agent_name: str) -> Dict[str, Any]:
    """Get configuration for a specific agent."""
    config = get_config()
    agents_config = config.get('agents', {})
    return agents_config.get(agent_name, {})


def get_prompt_template(template_name: str) -> str:
    """Get a prompt template by name."""
    config = get_config()
    openai_config = config.get('openai', {})
    prompts = openai_config.get('prompts', {})
    return prompts.get(template_name, "")


def get_database_config() -> Dict[str, Any]:
    """Get database configuration."""
    config = get_config()
    return config.get('database', {})


def get_logging_config() -> Dict[str, Any]:
    """Get logging configuration."""
    config = get_config()
    return config.get('logging', {})


def get_security_config() -> Dict[str, Any]:
    """Get security configuration."""
    config = get_config()
    return config.get('security', {})


def get_reconciliation_config() -> Dict[str, Any]:
    """Get reconciliation configuration."""
    config = get_config()
    return config.get('reconciliation', {})


def get_file_processing_config() -> Dict[str, Any]:
    """Get file processing configuration."""
    config = get_config()
    return config.get('file_processing', {})


def get_notification_config() -> Dict[str, Any]:
    """Get notification configuration."""
    config = get_config()
    return config.get('notifications', {})


def get_monitoring_config() -> Dict[str, Any]:
    """Get monitoring configuration."""
    config = get_config()
    return config.get('monitoring', {})


def get_api_config() -> Dict[str, Any]:
    """Get API configuration."""
    config = get_config()
    return config.get('api', {})


def get_ui_config() -> Dict[str, Any]:
    """Get UI configuration."""
    config = get_config()
    return config.get('ui', {})


def reload_config() -> None:
    """Reload configuration from files."""
    global _config_cache
    _config_cache = None
    load_config()


def get_environment() -> str:
    """Get the current environment."""
    return os.getenv('ENVIRONMENT', 'development')


def is_production() -> bool:
    """Check if running in production environment."""
    return get_environment() == 'production'


def is_development() -> bool:
    """Check if running in development environment."""
    return get_environment() == 'development'


def is_debug_enabled() -> bool:
    """Check if debug mode is enabled."""
    config = get_config()
    app_config = config.get('app', {})
    return app_config.get('debug', False)


def get_log_level() -> str:
    """Get the configured log level."""
    config = get_config()
    app_config = config.get('app', {})
    return app_config.get('log_level', 'INFO')


def get_database_url() -> str:
    """Get the database URL."""
    config = get_config()
    db_config = config.get('database', {})
    return db_config.get('url', os.getenv('DATABASE_URL', ''))


def get_redis_url() -> str:
    """Get the Redis URL."""
    config = get_config()
    return config.get('redis', {}).get('url', os.getenv('REDIS_URL', ''))


def get_openai_api_key() -> str:
    """Get the OpenAI API key."""
    config = get_config()
    openai_config = config.get('openai', {})
    api_config = openai_config.get('api', {})
    return api_config.get('api_key', os.getenv('OPENAI_API_KEY', ''))


def get_secret_key() -> str:
    """Get the application secret key."""
    config = get_config()
    security_config = config.get('security', {})
    return security_config.get('secret_key', os.getenv('SECRET_KEY', ''))


def get_jwt_secret_key() -> str:
    """Get the JWT secret key."""
    config = get_config()
    security_config = config.get('security', {})
    return security_config.get('jwt_secret_key', os.getenv('JWT_SECRET_KEY', ''))


# Import logging at the top to avoid circular imports
import logging 