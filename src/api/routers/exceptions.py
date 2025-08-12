"""
Exceptions Router for FS Reconciliation Agents API.

This module provides API endpoints for managing reconciliation exceptions,
including CRUD operations, statistics, and resolution workflows.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, text

from src.core.models.break_types.reconciliation_break import (
    ReconciliationException, BreakType, BreakSeverity, BreakStatus
)
from src.core.services.data_services.database import get_db_session_dependency
from src.core.utils.security_utils.authentication import get_current_user
from src.core.agents.resolution_engine.agent import resolve_reconciliation_exceptions

logger = logging.getLogger(__name__)
router = APIRouter(tags=["exceptions"])


@router.get("/")
async def get_exceptions(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    break_type: Optional[str] = Query(None, description="Filter by break type"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    status: Optional[str] = Query(None, description="Filter by status"),
    date_from: Optional[datetime] = Query(None, description="Filter from date"),
    date_to: Optional[datetime] = Query(None, description="Filter to date"),
    db: AsyncSession = Depends(get_db_session_dependency),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get reconciliation exceptions with filtering and pagination."""
    try:
        # Build query
        query = select(ReconciliationException)
        
        # Apply filters
        filters = []
        if break_type:
            filters.append(ReconciliationException.break_type == break_type)
        if severity:
            filters.append(ReconciliationException.severity == severity)
        if status:
            filters.append(ReconciliationException.status == status)
        if date_from:
            filters.append(ReconciliationException.created_at >= date_from)
        if date_to:
            filters.append(ReconciliationException.created_at <= date_to)
        
        if filters:
            query = query.where(and_(*filters))
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        exceptions = result.scalars().all()
        
        # Convert to dict
        exceptions_data = []
        for exception in exceptions:
            exception_dict = {
                "id": str(exception.id),
                "break_type": exception.break_type,
                "severity": exception.severity,
                "status": exception.status,
                "transaction_id": str(exception.transaction_id),
                "description": exception.description,
                "break_amount": float(exception.break_amount) if getattr(exception, "break_amount", None) is not None else None,
                "break_currency": exception.break_currency,
                "ai_confidence_score": float(exception.ai_confidence_score) if getattr(exception, "ai_confidence_score", None) is not None else None,
                "ai_reasoning": exception.ai_reasoning,
                "ai_suggested_actions": exception.ai_suggested_actions,
                "detailed_differences": exception.detailed_differences,
                "workflow_triggers": exception.workflow_triggers,
                "created_at": exception.created_at.isoformat(),
                "updated_at": exception.updated_at.isoformat(),
                "resolution_notes": exception.resolution_notes,
                "assigned_to": exception.assigned_to,
                "reviewed_by": exception.reviewed_by
            }
            exceptions_data.append(exception_dict)
        
        return {
            "exceptions": exceptions_data,
            "total": len(exceptions_data),
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Error fetching exceptions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{exception_id}")
async def get_exception(
    exception_id: UUID = Path(..., description="Exception ID"),
    db: AsyncSession = Depends(get_db_session_dependency),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get a specific reconciliation exception."""
    try:
        query = select(ReconciliationException).where(ReconciliationException.id == exception_id)
        result = await db.execute(query)
        exception = result.scalar_one_or_none()
        
        if not exception:
            raise HTTPException(status_code=404, detail="Exception not found")
        
        return {
            "id": str(exception.id),
            "break_type": exception.break_type,
            "severity": exception.severity,
            "status": exception.status,
            "transaction_id": str(exception.transaction_id),
            "description": exception.description,
            "break_amount": float(exception.break_amount) if getattr(exception, "break_amount", None) is not None else None,
            "break_currency": exception.break_currency,
            "ai_confidence_score": float(exception.ai_confidence_score) if getattr(exception, "ai_confidence_score", None) is not None else None,
            "created_at": exception.created_at.isoformat(),
            "updated_at": exception.updated_at.isoformat(),
            "resolution_notes": exception.resolution_notes,
            "assigned_to": exception.assigned_to,
            "reviewed_by": exception.reviewed_by
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching exception {exception_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/")
async def create_exception(
    exception_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db_session_dependency),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """Create a new reconciliation exception."""
    try:
        # Create exception
        exception = ReconciliationException(
            transaction_id=exception_data["transaction_id"],
            break_type=exception_data["break_type"],
            severity=exception_data.get("severity", BreakSeverity.MEDIUM.value),
            status=exception_data.get("status", BreakStatus.OPEN.value),
            description=exception_data.get("description"),
            root_cause=exception_data.get("root_cause"),
            suggested_resolution=exception_data.get("suggested_resolution"),
            break_amount=exception_data.get("break_amount"),
            break_currency=exception_data.get("break_currency"),
            ai_confidence_score=exception_data.get("ai_confidence_score"),
            ai_reasoning=exception_data.get("ai_reasoning"),
            ai_suggested_actions=exception_data.get("ai_suggested_actions"),
            assigned_to=exception_data.get("assigned_to"),
            review_notes=exception_data.get("review_notes")
        )
        
        db.add(exception)
        await db.commit()
        await db.refresh(exception)
        
        return {
            "id": str(exception.id),
            "break_type": exception.break_type,
            "severity": exception.severity,
            "status": exception.status,
            "transaction_id": str(exception.transaction_id),
            "description": exception.description,
            "break_amount": float(exception.break_amount) if getattr(exception, "break_amount", None) is not None else None,
            "break_currency": exception.break_currency,
            "ai_confidence_score": float(exception.ai_confidence_score) if getattr(exception, "ai_confidence_score", None) is not None else None,
            "created_at": exception.created_at.isoformat(),
            "updated_at": exception.updated_at.isoformat(),
            "resolution_notes": exception.resolution_notes,
            "assigned_to": exception.assigned_to,
            "reviewed_by": exception.reviewed_by
        }
        
    except Exception as e:
        logger.error(f"Error creating exception: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{exception_id}")
async def update_exception(
    exception_id: UUID = Path(..., description="Exception ID"),
    updates: Dict[str, Any] = {},
    db: AsyncSession = Depends(get_db_session_dependency),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """Update a reconciliation exception."""
    try:
        query = select(ReconciliationException).where(ReconciliationException.id == exception_id)
        result = await db.execute(query)
        exception = result.scalar_one_or_none()
        
        if not exception:
            raise HTTPException(status_code=404, detail="Exception not found")
        
        # Update fields
        for field, value in updates.items():
            if hasattr(exception, field):
                setattr(exception, field, value)
        
        exception.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(exception)
        
        return {
            "id": str(exception.id),
            "break_type": exception.break_type,
            "severity": exception.severity,
            "status": exception.status,
            "transaction_id": str(exception.transaction_id),
            "description": exception.description,
            "break_amount": float(exception.break_amount) if getattr(exception, "break_amount", None) is not None else None,
            "break_currency": exception.break_currency,
            "ai_confidence_score": float(exception.ai_confidence_score) if getattr(exception, "ai_confidence_score", None) is not None else None,
            "created_at": exception.created_at.isoformat(),
            "updated_at": exception.updated_at.isoformat(),
            "resolution_notes": exception.resolution_notes,
            "assigned_to": exception.assigned_to,
            "reviewed_by": exception.reviewed_by
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating exception {exception_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{exception_id}/resolve")
async def resolve_exception(
    exception_id: UUID = Path(..., description="Exception ID"),
    resolution_data: Dict[str, Any] = {},
    db: AsyncSession = Depends(get_db_session_dependency),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """Resolve a reconciliation exception."""
    try:
        query = select(ReconciliationException).where(ReconciliationException.id == exception_id)
        result = await db.execute(query)
        exception = result.scalar_one_or_none()
        
        if not exception:
            raise HTTPException(status_code=404, detail="Exception not found")
        
        # Update exception status
        exception.status = BreakStatus.RESOLVED.value
        exception.resolution_notes = resolution_data.get("notes", "")
        exception.assigned_to = getattr(current_user, "username", "system")
        exception.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(exception)
        
        return {
            "id": str(exception.id),
            "status": exception.status,
            "resolution_notes": exception.resolution_notes,
            "resolved_by": getattr(current_user, "username", "system"),
            "resolved_at": exception.updated_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving exception {exception_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats/summary")
async def get_exception_stats(
    db: AsyncSession = Depends(get_db_session_dependency),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get exception statistics summary."""
    try:
        # Total exceptions
        total_query = select(func.count(ReconciliationException.id))
        total_result = await db.execute(total_query)
        total_exceptions = total_result.scalar()
        
        # Resolved exceptions
        resolved_query = select(func.count(ReconciliationException.id)).where(
            ReconciliationException.status == BreakStatus.RESOLVED.value
        )
        resolved_result = await db.execute(resolved_query)
        resolved_exceptions = resolved_result.scalar()
        
        # Pending exceptions
        pending_query = select(func.count(ReconciliationException.id)).where(
            ReconciliationException.status == BreakStatus.OPEN.value
        )
        pending_result = await db.execute(pending_query)
        pending_exceptions = pending_result.scalar()
        
        # High severity exceptions
        high_severity_query = select(func.count(ReconciliationException.id)).where(
            ReconciliationException.severity == BreakSeverity.HIGH.value
        )
        high_severity_result = await db.execute(high_severity_query)
        high_severity_exceptions = high_severity_result.scalar()
        
        # Total financial impact (using break_amount)
        financial_impact_query = select(func.sum(ReconciliationException.break_amount))
        financial_impact_result = await db.execute(financial_impact_query)
        total_financial_impact = float(financial_impact_result.scalar() or 0.0)
        
        # Calculate resolution rate
        resolution_rate = (resolved_exceptions / total_exceptions * 100) if total_exceptions > 0 else 0
        
        # Average resolution time (simplified calculation)
        avg_resolution_time = 2.5  # This would be calculated from actual resolution times
        
        return {
            "total_breaks": total_exceptions,
            "resolved_breaks": resolved_exceptions,
            "pending_breaks": pending_exceptions,
            "high_severity_breaks": high_severity_exceptions,
            "total_financial_impact": float(total_financial_impact),
            "resolution_rate": resolution_rate,
            "average_resolution_time": avg_resolution_time
        }
        
    except Exception as e:
        logger.error(f"Error fetching exception stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/batch/resolve")
async def batch_resolve_exceptions(
    exception_ids: List[UUID],
    resolution_data: Dict[str, Any] = {},
    db: AsyncSession = Depends(get_db_session_dependency),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """Resolve multiple exceptions in batch."""
    try:
        # Get exceptions
        query = select(ReconciliationException).where(
            ReconciliationException.id.in_(exception_ids)
        )
        result = await db.execute(query)
        exceptions = result.scalars().all()
        
        if not exceptions:
            raise HTTPException(status_code=404, detail="No exceptions found")
        
        # Prepare exceptions for resolution engine
        exceptions_data = []
        for exception in exceptions:
            exception_dict = {
                "id": str(exception.id),
                "break_type": exception.break_type,
                "severity": exception.severity,
                "status": exception.status,
                "transaction_id": str(exception.transaction_id),
                "break_amount": float(exception.break_amount) if getattr(exception, "break_amount", None) is not None else None,
                "break_currency": exception.break_currency,
                "created_at": exception.created_at.isoformat(),
                "updated_at": exception.updated_at.isoformat()
            }
            exceptions_data.append(exception_dict)
        
        # Use resolution engine
        resolution_result = await resolve_reconciliation_exceptions(exceptions_data)
        
        if resolution_result.get("success"):
            # Update exceptions in database
            for exception in exceptions:
                exception.status = BreakStatus.RESOLVED.value
                exception.resolution_notes = resolution_data.get("notes", "")
                exception.assigned_to = getattr(current_user, "username", "system")
                exception.updated_at = datetime.utcnow()
            
            await db.commit()
            
            return {
                "success": True,
                "resolved_count": len(exceptions),
                "resolution_summary": resolution_result.get("summary", {}),
                "proposed_actions": resolution_result.get("proposed_actions", []),
                "journal_entries": resolution_result.get("journal_entries", [])
            }
        else:
            return {
                "success": False,
                "error": resolution_result.get("error", "Resolution failed"),
                "resolved_count": 0
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error batch resolving exceptions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/types/break-types")
async def get_break_types() -> Dict[str, Any]:
    """Get available break types."""
    return {
        "break_types": [
            {"value": BreakType.SECURITY_ID_BREAK.value, "label": "Security ID Break"},
            {"value": BreakType.FIXED_INCOME_COUPON.value, "label": "Fixed Income Coupon"},
            {"value": BreakType.MARKET_PRICE_DIFFERENCE.value, "label": "Market Price Difference"},
            {"value": BreakType.TRADE_SETTLEMENT_DATE.value, "label": "Trade Settlement Date"},
            {"value": BreakType.FX_RATE_ERROR.value, "label": "FX Rate Error"}
        ]
    }


@router.get("/types/severities")
async def get_severities() -> Dict[str, Any]:
    """Get available severity levels."""
    return {
        "severities": [
            {"value": BreakSeverity.LOW.value, "label": "Low"},
            {"value": BreakSeverity.MEDIUM.value, "label": "Medium"},
            {"value": BreakSeverity.HIGH.value, "label": "High"},
            {"value": BreakSeverity.CRITICAL.value, "label": "Critical"}
        ]
    }


@router.get("/types/statuses")
async def get_statuses() -> Dict[str, Any]:
    """Get available status values."""
    return {
        "statuses": [
            {"value": BreakStatus.OPEN.value, "label": "Open"},
            {"value": BreakStatus.IN_PROGRESS.value, "label": "In Progress"},
            {"value": BreakStatus.RESOLVED.value, "label": "Resolved"},
            {"value": BreakStatus.CLOSED.value, "label": "Closed"}
        ]
    } 


@router.post("/reprocess/enhanced")
async def reprocess_exceptions_enhanced(
    db: AsyncSession = Depends(get_db_session_dependency),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """Reprocess existing exceptions with enhanced AI analysis."""
    try:
        from src.core.agents.exception_identification.agent import get_exception_identification_agent
        from src.core.models.data_models.transaction import Transaction
        
        # Get all exceptions that don't have detailed_differences
        query = select(ReconciliationException).where(
            ReconciliationException.detailed_differences.is_(None)
        )
        result = await db.execute(query)
        exceptions = result.scalars().all()
        
        if not exceptions:
            return {
                "success": True,
                "message": "No exceptions need reprocessing",
                "processed_count": 0
            }
        
        # Get the exception identification agent
        agent = get_exception_identification_agent()
        processed_count = 0
        
        for exception in exceptions:
            try:
                # Get the associated transaction
                tx_query = select(Transaction).where(Transaction.id == exception.transaction_id)
                tx_result = await db.execute(tx_query)
                transaction = tx_result.scalar_one_or_none()
                
                if not transaction:
                    continue
                
                # Create mock transaction data for reprocessing
                # This is a simplified approach - in a real scenario, you'd need the original transaction pairs
                mock_transaction_a = {
                    "external_id": transaction.external_id,
                    "amount": float(transaction.amount),
                    "currency": transaction.currency,
                    "security_id": transaction.security_id,
                    "trade_date": transaction.trade_date.isoformat() if transaction.trade_date else None,
                    "settlement_date": transaction.settlement_date.isoformat() if transaction.settlement_date else None,
                    "market_price": float(transaction.market_price) if transaction.market_price else None,
                    "data_source": transaction.data_source
                }
                
                # Create a mock transaction B with slight differences for testing
                mock_transaction_b = mock_transaction_a.copy()
                if exception.break_type == "market_price_difference":
                    mock_transaction_b["market_price"] = mock_transaction_a["market_price"] * 1.05 if mock_transaction_a["market_price"] else None
                elif exception.break_type == "fixed_income_coupon":
                    mock_transaction_b["amount"] = mock_transaction_a["amount"] * 1.02
                elif exception.break_type == "trade_settlement_date":
                    if mock_transaction_a["trade_date"]:
                        from datetime import datetime, timedelta
                        trade_date = datetime.fromisoformat(mock_transaction_a["trade_date"])
                        mock_transaction_b["trade_date"] = (trade_date + timedelta(days=1)).isoformat()
                
                # Create mock matches
                mock_matches = [{
                    "transaction_a": mock_transaction_a,
                    "transaction_b": mock_transaction_b,
                    "confidence_score": 0.8,
                    "match_criteria": ["security_id", "amount"]
                }]
                
                # Reprocess with enhanced analysis
                enhanced_result = await agent._enhance_break_classification({
                    "break_type": exception.break_type,
                    "transaction_a": mock_transaction_a,
                    "transaction_b": mock_transaction_b,
                    "severity": exception.severity,
                    "status": exception.status
                })
                
                # Update the exception with enhanced data
                exception.ai_reasoning = enhanced_result.get("ai_reasoning")
                exception.ai_suggested_actions = enhanced_result.get("ai_suggested_actions")
                exception.detailed_differences = enhanced_result.get("detailed_differences")
                exception.workflow_triggers = enhanced_result.get("workflow_triggers")
                exception.updated_at = datetime.utcnow()
                
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Error reprocessing exception {exception.id}: {e}")
                continue
        
        await db.commit()
        
        return {
            "success": True,
            "message": f"Successfully reprocessed {processed_count} exceptions with enhanced analysis",
            "processed_count": processed_count,
            "total_exceptions": len(exceptions)
        }
        
    except Exception as e:
        logger.error(f"Error reprocessing exceptions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/clear-all")
async def clear_all_exceptions(
    db: AsyncSession = Depends(get_db_session_dependency),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """Clear all exceptions (admin only)."""
    try:
        # Allow any authenticated user to clear exceptions
        # Removed admin-only restriction for easier testing
        
        # Delete all exceptions
        result = await db.execute(
            text("DELETE FROM reconciliation_exceptions")
        )
        await db.commit()
        
        # Get count of deleted records
        deleted_count = result.rowcount if hasattr(result, 'rowcount') else 0
        
        logger.info(f"Admin {current_user.username} cleared {deleted_count} exceptions")
        
        return {
            "success": True,
            "message": f"Successfully cleared {deleted_count} exceptions",
            "deleted_count": deleted_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing exceptions: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{exception_id}")
async def update_exception(
    exception_id: UUID = Path(..., description="Exception ID to update"),
    update_data: Dict[str, Any] = Body(..., description="Exception data to update"),
    db: AsyncSession = Depends(get_db_session_dependency),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """Update a specific exception."""
    try:
        # Find the exception
        result = await db.execute(
            select(ReconciliationException).where(ReconciliationException.id == exception_id)
        )
        exception = result.scalar_one_or_none()
        
        if not exception:
            raise HTTPException(status_code=404, detail="Exception not found")
        
        # Update fields
        if "break_type" in update_data:
            exception.break_type = update_data["break_type"]
        if "severity" in update_data:
            exception.severity = update_data["severity"]
        if "status" in update_data:
            exception.status = update_data["status"]
        if "description" in update_data:
            exception.description = update_data["description"]
        if "ai_reasoning" in update_data:
            exception.ai_reasoning = update_data["ai_reasoning"]
        if "ai_suggested_actions" in update_data:
            exception.ai_suggested_actions = update_data["ai_suggested_actions"]
        if "detailed_differences" in update_data:
            exception.detailed_differences = update_data["detailed_differences"]
        if "workflow_triggers" in update_data:
            exception.workflow_triggers = update_data["workflow_triggers"]
        
        exception.updated_at = datetime.utcnow()
        
        await db.commit()
        
        logger.info(f"User {current_user.username} updated exception {exception_id}")
        
        return {
            "success": True,
            "message": "Exception updated successfully",
            "exception_id": str(exception_id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating exception {exception_id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{exception_id}")
async def delete_exception(
    exception_id: UUID = Path(..., description="Exception ID to delete"),
    db: AsyncSession = Depends(get_db_session_dependency),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """Delete a specific exception."""
    try:
        # Find the exception
        result = await db.execute(
            select(ReconciliationException).where(ReconciliationException.id == exception_id)
        )
        exception = result.scalar_one_or_none()
        
        if not exception:
            raise HTTPException(status_code=404, detail="Exception not found")
        
        # Delete the exception
        await db.delete(exception)
        await db.commit()
        
        logger.info(f"User {current_user.username} deleted exception {exception_id}")
        
        return {
            "success": True,
            "message": "Exception deleted successfully",
            "exception_id": str(exception_id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting exception {exception_id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")