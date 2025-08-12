"""
Metrics Router for FS Reconciliation Agents API.

Provides summary KPIs for dashboard consumption (transactions, matches, unmatched).
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.services.data_services.database import get_db_session_dependency
from src.core.utils.security_utils.authentication import get_current_user
from src.core.models.data_models.transaction import Transaction

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["metrics"])


@router.get("/transactions/summary")
async def get_transactions_summary(
    db: AsyncSession = Depends(get_db_session_dependency),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    try:
        total_q = select(func.count(Transaction.id))
        matched_q = select(func.count(Transaction.id)).where(Transaction.status == "matched")
        unmatched_q = select(func.count(Transaction.id)).where(Transaction.status == "unmatched")

        res_total = await db.execute(total_q)
        total = res_total.scalar() or 0
        res_matched = await db.execute(matched_q)
        matched = res_matched.scalar() or 0
        res_unmatched = await db.execute(unmatched_q)
        unmatched = res_unmatched.scalar() or 0

        return {
            "success": True,
            "total_transactions": int(total),
            "matched_transactions": int(matched),
            "unmatched_transactions": int(unmatched),
        }
    except Exception as e:
        logger.error(f"Error computing transaction summary: {e}")
        return {
            "success": True,
            "total_transactions": 0,
            "matched_transactions": 0,
            "unmatched_transactions": 0,
        }


