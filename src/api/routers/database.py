from fastapi import APIRouter, HTTPException, Query, Depends, Body
from typing import List, Dict, Any, Optional
from sqlalchemy import text, select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.services.data_services.database import get_db_session
from src.core.utils.security_utils.authentication import get_current_user
from src.core.models.data_models.transaction import Transaction, TransactionMatch
from src.core.models.break_types.reconciliation_break import ReconciliationException
from src.core.models.audit_models.audit_trail import AuditTrail, SystemLog
import json
from datetime import datetime

router = APIRouter(prefix="/database", tags=["database"])

# Table configurations
TABLE_CONFIGS = {
    "transactions": {
        "model": Transaction,
        "display_name": "Transactions",
        "columns": [
            {"name": "id", "display": "ID", "type": "uuid", "editable": False},
            {"name": "external_id", "display": "External ID", "type": "string", "editable": True},
            {"name": "transaction_type", "display": "Type", "type": "string", "editable": True},
            {"name": "status", "display": "Status", "type": "string", "editable": True},
            {"name": "amount", "display": "Amount", "type": "numeric", "editable": True},
            {"name": "currency", "display": "Currency", "type": "string", "editable": True},
            {"name": "security_id", "display": "Security ID", "type": "string", "editable": True},
            {"name": "data_source", "display": "Data Source", "type": "string", "editable": True},
            {"name": "created_at", "display": "Created", "type": "datetime", "editable": False}
        ],
        "filters": ["external_id", "transaction_type", "status", "data_source", "security_id"]
    },
    "reconciliation_exceptions": {
        "model": ReconciliationException,
        "display_name": "Reconciliation Exceptions",
        "columns": [
            {"name": "id", "display": "ID", "type": "uuid", "editable": False},
            {"name": "break_type", "display": "Break Type", "type": "string", "editable": True},
            {"name": "severity", "display": "Severity", "type": "string", "editable": True},
            {"name": "status", "display": "Status", "type": "string", "editable": True},
            {"name": "description", "display": "Description", "type": "string", "editable": True},
            {"name": "ai_reasoning", "display": "AI Reasoning", "type": "text", "editable": True},
            {"name": "created_at", "display": "Created", "type": "datetime", "editable": False}
        ],
        "filters": ["break_type", "severity", "status"]
    },
    "transaction_matches": {
        "model": TransactionMatch,
        "display_name": "Transaction Matches",
        "columns": [
            {"name": "id", "display": "ID", "type": "uuid", "editable": False},
            {"name": "match_type", "display": "Match Type", "type": "string", "editable": True},
            {"name": "confidence_score", "display": "Confidence", "type": "numeric", "editable": True},
            {"name": "status", "display": "Status", "type": "string", "editable": True},
            {"name": "created_at", "display": "Created", "type": "datetime", "editable": False}
        ],
        "filters": ["match_type", "status"]
    },
    "system_logs": {
        "model": SystemLog,
        "display_name": "System Logs",
        "columns": [
            {"name": "id", "display": "ID", "type": "uuid", "editable": False},
            {"name": "log_level", "display": "Level", "type": "string", "editable": False},
            {"name": "component", "display": "Component", "type": "string", "editable": False},
            {"name": "log_message", "display": "Message", "type": "text", "editable": False},
            {"name": "created_at", "display": "Created", "type": "datetime", "editable": False}
        ],
        "filters": ["log_level", "component"]
    },
    "audit_trail": {
        "model": AuditTrail,
        "display_name": "Audit Trail",
        "columns": [
            {"name": "id", "display": "ID", "type": "uuid", "editable": False},
            {"name": "action_type", "display": "Action", "type": "string", "editable": False},
            {"name": "user_name", "display": "User", "type": "string", "editable": False},
            {"name": "entity_type", "display": "Entity", "type": "string", "editable": False},
            {"name": "severity", "display": "Severity", "type": "string", "editable": False},
            {"name": "created_at", "display": "Created", "type": "datetime", "editable": False}
        ],
        "filters": ["action_type", "user_name", "entity_type", "severity"]
    }
}

@router.get("/tables")
async def get_available_tables():
    """Get list of available database tables with their configurations."""
    return {
        "success": True,
        "tables": {
            table_name: {
                "display_name": config["display_name"],
                "columns": config["columns"],
                "filters": config["filters"]
            }
            for table_name, config in TABLE_CONFIGS.items()
        }
    }

@router.get("/{table_name}")
async def get_table_data(
    table_name: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    filters: Optional[str] = Query(None, description="JSON string of filters"),
    sort_by: Optional[str] = Query(None),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    current_user = Depends(get_current_user)
):
    """Get data from a specific table with filtering and pagination."""
    if table_name not in TABLE_CONFIGS:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    
    config = TABLE_CONFIGS[table_name]
    model = config["model"]
    
    try:
        async with get_db_session() as session:
            # Build query
            query = select(model)
            
            # Apply filters
            if filters:
                try:
                    filter_dict = json.loads(filters)
                    for field, value in filter_dict.items():
                        if field in config["filters"] and value:
                            if hasattr(model, field):
                                query = query.where(getattr(model, field).ilike(f"%{value}%"))
                except json.JSONDecodeError:
                    raise HTTPException(status_code=400, detail="Invalid filters JSON")
            
            # Apply sorting
            if sort_by and hasattr(model, sort_by):
                if sort_order == "desc":
                    query = query.order_by(desc(getattr(model, sort_by)))
                else:
                    query = query.order_by(getattr(model, sort_by))
            else:
                # Default sorting by created_at or id
                if hasattr(model, "created_at"):
                    query = query.order_by(desc(model.created_at))
                else:
                    query = query.order_by(desc(model.id))
            
            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            total_count = await session.scalar(count_query)
            
            # Apply pagination
            query = query.offset(skip).limit(limit)
            
            # Execute query
            result = await session.execute(query)
            records = result.scalars().all()
            
            # Convert to dictionaries
            data = []
            for record in records:
                record_dict = {}
                for column in config["columns"]:
                    value = getattr(record, column["name"], None)
                    if isinstance(value, datetime):
                        value = value.isoformat()
                    record_dict[column["name"]] = value
                data.append(record_dict)
            
            return {
                "success": True,
                "data": data,
                "total_count": total_count,
                "skip": skip,
                "limit": limit,
                "table_config": {
                    "display_name": config["display_name"],
                    "columns": config["columns"]
                }
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.put("/{table_name}/{record_id}")
async def update_record(
    table_name: str,
    record_id: str,
    updates: Dict[str, Any] = Body(...),
    current_user = Depends(get_current_user)
):
    """Update a specific record in a table."""
    if table_name not in TABLE_CONFIGS:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    
    config = TABLE_CONFIGS[table_name]
    model = config["model"]
    
    # Validate editable fields
    editable_columns = {col["name"] for col in config["columns"] if col["editable"]}
    invalid_fields = set(updates.keys()) - editable_columns
    if invalid_fields:
        raise HTTPException(status_code=400, detail=f"Cannot edit fields: {invalid_fields}")
    
    try:
        async with get_db_session() as session:
            # Get record
            query = select(model).where(model.id == record_id)
            result = await session.execute(query)
            record = result.scalar_one_or_none()
            
            if not record:
                raise HTTPException(status_code=404, detail="Record not found")
            
            # Update fields
            for field, value in updates.items():
                if hasattr(record, field):
                    setattr(record, field, value)
            
            # Update timestamp if available
            if hasattr(record, "updated_at"):
                record.updated_at = datetime.utcnow()
            
            await session.commit()
            
            return {"success": True, "message": "Record updated successfully"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update error: {str(e)}")

@router.delete("/{table_name}/bulk")
async def bulk_delete_records(
    table_name: str,
    record_ids: List[str] = Body(...),
    current_user = Depends(get_current_user)
):
    """Delete multiple records from a table."""
    if table_name not in TABLE_CONFIGS:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    
    config = TABLE_CONFIGS[table_name]
    model = config["model"]
    
    try:
        async with get_db_session() as session:
            # Delete records
            deleted_count = 0
            for record_id in record_ids:
                query = select(model).where(model.id == record_id)
                result = await session.execute(query)
                record = result.scalar_one_or_none()
                
                if record:
                    await session.delete(record)
                    deleted_count += 1
            
            await session.commit()
            
            return {
                "success": True, 
                "message": f"Deleted {deleted_count} records successfully",
                "deleted_count": deleted_count
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bulk delete error: {str(e)}")

@router.delete("/{table_name}/{record_id}")
async def delete_record(
    table_name: str,
    record_id: str,
    current_user = Depends(get_current_user)
):
    """Delete a specific record from a table."""
    if table_name not in TABLE_CONFIGS:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    
    config = TABLE_CONFIGS[table_name]
    model = config["model"]
    
    try:
        async with get_db_session() as session:
            # Get record
            query = select(model).where(model.id == record_id)
            result = await session.execute(query)
            record = result.scalar_one_or_none()
            
            if not record:
                raise HTTPException(status_code=404, detail="Record not found")
            
            await session.delete(record)
            await session.commit()
            
            return {"success": True, "message": "Record deleted successfully"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete error: {str(e)}")

@router.get("/{table_name}/stats")
async def get_table_stats(
    table_name: str,
    current_user = Depends(get_current_user)
):
    """Get statistics for a table."""
    if table_name not in TABLE_CONFIGS:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    
    config = TABLE_CONFIGS[table_name]
    model = config["model"]
    
    try:
        async with get_db_session() as session:
            # Get total count
            count_query = select(func.count()).select_from(model)
            total_count = await session.scalar(count_query)
            
            # Get recent activity (last 24 hours)
            recent_query = select(func.count()).select_from(model)
            if hasattr(model, "created_at"):
                recent_query = recent_query.where(
                    model.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                )
            recent_count = await session.scalar(recent_query)
            
            # Get column statistics if applicable
            column_stats = {}
            for column in config["columns"]:
                if column["type"] in ["string", "numeric"] and column["name"] != "id":
                    try:
                        if column["type"] == "string":
                            # Get unique values count
                            unique_query = select(func.count(func.distinct(getattr(model, column["name"]))))
                            unique_count = await session.scalar(unique_query)
                            column_stats[column["name"]] = {"unique_values": unique_count}
                        elif column["type"] == "numeric":
                            # Get min, max, avg
                            stats_query = select(
                                func.min(getattr(model, column["name"])),
                                func.max(getattr(model, column["name"])),
                                func.avg(getattr(model, column["name"]))
                            )
                            result = await session.execute(stats_query)
                            min_val, max_val, avg_val = result.first()
                            column_stats[column["name"]] = {
                                "min": float(min_val) if min_val else None,
                                "max": float(max_val) if max_val else None,
                                "avg": float(avg_val) if avg_val else None
                            }
                    except Exception:
                        # Skip columns that can't be analyzed
                        pass
            
            return {
                "success": True,
                "stats": {
                    "total_records": total_count,
                    "recent_records": recent_count,
                    "column_stats": column_stats
                }
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats error: {str(e)}")
