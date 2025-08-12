"""
Settings Router for FS Reconciliation Agents API.

Provides simple persistence for UI settings (thresholds, notifications).
Stores settings in the database if a table exists; otherwise falls back to a JSON file.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from src.core.services.data_services.database import get_db_session_dependency
from src.core.utils.security_utils.authentication import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/settings", tags=["settings"])

SETTINGS_FILE = Path("data/config/ui_settings.json")
SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)


async def _db_has_settings_table(db: AsyncSession) -> bool:
    try:
        result = await db.execute(text("""
            SELECT to_regclass('public.ui_settings')
        """))
        val = result.scalar()
        return bool(val)
    except Exception:
        return False


@router.get("/")
async def get_settings(
    db: AsyncSession = Depends(get_db_session_dependency),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """Fetch UI settings.
    Tries DB first, falls back to JSON file. Returns empty defaults if neither available.
    """
    try:
        if await _db_has_settings_table(db):
            result = await db.execute(text("""
                SELECT settings_json FROM ui_settings WHERE id = 1
            """))
            row = result.first()
            if row and row[0]:
                return {"success": True, "settings": row[0]}
        # Fallback to file
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, 'r') as f:
                return {"success": True, "settings": json.load(f)}
        return {"success": True, "settings": {}}
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/")
async def save_settings(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db_session_dependency),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """Persist UI settings.
    Creates a simple single-row table if missing; otherwise writes a JSON file fallback.
    """
    try:
        settings = payload.get("settings", {})
        # Try DB first
        try:
            await db.execute(text("""
                CREATE TABLE IF NOT EXISTS ui_settings (
                    id INT PRIMARY KEY,
                    settings_json JSONB NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            await db.execute(text("""
                INSERT INTO ui_settings (id, settings_json)
                VALUES (1, :settings)
                ON CONFLICT (id) DO UPDATE SET
                    settings_json = EXCLUDED.settings_json,
                    updated_at = NOW()
            """), {"settings": json.dumps(settings)})
            await db.commit()
            return {"success": True}
        except Exception as db_err:
            logger.warning(f"DB settings persistence failed, using file fallback: {db_err}")
        # Fallback to file
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        return {"success": True}
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


