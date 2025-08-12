"""
Core models package for FS Reconciliation Agents.

This package contains all the data models used throughout the application.
"""

from sqlalchemy.ext.declarative import declarative_base

# Shared Base for all models to ensure they're in the same registry
Base = declarative_base()

__all__ = ['Base']
