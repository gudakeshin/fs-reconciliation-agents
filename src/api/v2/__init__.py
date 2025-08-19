"""
FS Reconciliation Agents API v2.

Enhanced API with improved features:
- Better error handling
- Comprehensive validation
- Rate limiting
- Enhanced documentation
- WebSocket support
- Real-time updates
"""

from .main_simple import app

__version__ = "2.0.0"
__all__ = ["app"]
