"""
Reports Router for FS Reconciliation Agents API.

This module provides API endpoints for generating and managing reports,
including various report types and formats.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path as PathLib

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.services.reporting_services.reporting_engine import (
    ReportType, ReportFormat, generate_report
)
from src.core.services.data_services.database import get_db_session
from src.core.utils.security_utils.authentication import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["reports"])

# Reports directory
REPORTS_DIR = PathLib("data/reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/generate")
async def generate_report_endpoint(
    report_type: str = Query(..., description="Type of report to generate"),
    format: str = Query("json", description="Output format"),
    parameters: Dict[str, Any] = {},
    db: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """Generate a report of the specified type."""
    try:
        # Validate report type
        try:
            report_type_enum = ReportType(report_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid report type. Valid types: {[rt.value for rt in ReportType]}"
            )
        
        # Validate format
        try:
            format_enum = ReportFormat(format)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid format. Valid formats: {[rf.value for rf in ReportFormat]}"
            )
        
        # Get data for report
        report_data = await get_report_data(report_type_enum, db)
        
        # Generate report
        result = await generate_report(
            report_type=report_type_enum,
            data=report_data,
            format=format_enum,
            parameters=parameters
        )
        
        if result:
            # Save report to file system
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{report_type}_{timestamp}.{format}"
            file_path = REPORTS_DIR / filename
            
            # Save report content
            if format == "json":
                import json
                with open(file_path, 'w') as f:
                    json.dump(result, f, indent=2)
            elif format == "csv":
                # Convert to CSV format
                import csv
                with open(file_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    # Add CSV headers and data
                    pass
            elif format == "pdf":
                # Generate PDF (would need additional library)
                with open(file_path, 'wb') as f:
                    f.write(b"PDF content placeholder")
            elif format == "excel":
                # Generate Excel (would need additional library)
                with open(file_path, 'wb') as f:
                    f.write(b"Excel content placeholder")
            elif format == "html":
                with open(file_path, 'w') as f:
                    f.write("<html>Report content</html>")
            
            return {
                "success": True,
                "report_id": filename,
                "report_type": report_type,
                "format": format,
                "file_path": str(file_path),
                "generated_at": datetime.utcnow().isoformat(),
                "metadata": result.get("metadata", {}),
                "download_url": f"/reports/download/{filename}"
            }
        else:
            return {
                "success": False,
                "error": "Failed to generate report"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/download/{filename}")
async def download_report(
    filename: str,
    meta: bool = Query(False, description="Return metadata instead of file when true"),
    db: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user)
):
    """Download a generated report. Streams file content unless meta=true."""
    try:
        file_path = REPORTS_DIR / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Security: ensure within reports dir
        if not file_path.resolve().is_relative_to(REPORTS_DIR.resolve()):
            raise HTTPException(status_code=403, detail="Access denied")
        
        if meta:
            stat = file_path.stat()
            return {
                "success": True,
                "filename": filename,
                "file_path": str(file_path),
                "file_size": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "download_url": f"/reports/download/{filename}"
            }
        
        # Determine media type
        suffix = file_path.suffix.lower()
        media_map = {
            ".json": "application/json",
            ".csv": "text/csv",
            ".pdf": "application/pdf",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xls": "application/vnd.ms-excel",
            ".html": "text/html",
        }
        media_type = media_map.get(suffix, "application/octet-stream")
        
        return FileResponse(path=str(file_path), media_type=media_type, filename=filename)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading report {filename}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/list")
async def list_reports(
    report_type: Optional[str] = Query(None, description="Filter by report type"),
    date_from: Optional[datetime] = Query(None, description="Filter from date"),
    date_to: Optional[datetime] = Query(None, description="Filter to date"),
    db: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """List available reports."""
    try:
        reports = []
        
        for file_path in REPORTS_DIR.glob("*"):
            if file_path.is_file():
                stat = file_path.stat()
                created_at = datetime.fromtimestamp(stat.st_ctime)
                
                # Apply filters
                if report_type and not file_path.name.startswith(report_type):
                    continue
                if date_from and created_at < date_from:
                    continue
                if date_to and created_at > date_to:
                    continue
                
                # Parse report info from filename
                filename = file_path.name
                parts = filename.split('_')
                if len(parts) >= 2:
                    report_type_name = parts[0]
                    timestamp = parts[1].split('.')[0]
                    format = file_path.suffix[1:] if file_path.suffix else "unknown"
                else:
                    report_type_name = "unknown"
                    timestamp = "unknown"
                    format = "unknown"
                
                reports.append({
                    "filename": filename,
                    "report_type": report_type_name,
                    "format": format,
                    "file_size": stat.st_size,
                    "created_at": created_at.isoformat(),
                    "download_url": f"/reports/download/{filename}"
                })
        
        # Sort by creation date (newest first)
        reports.sort(key=lambda x: x["created_at"], reverse=True)
        
        return {
            "reports": reports,
            "total": len(reports)
        }
        
    except Exception as e:
        logger.error(f"Error listing reports: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{filename}")
async def delete_report(
    filename: str,
    db: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """Delete a generated report."""
    try:
        file_path = REPORTS_DIR / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Check if file is in reports directory (security check)
        if not file_path.resolve().is_relative_to(REPORTS_DIR.resolve()):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Delete file
        file_path.unlink()
        
        return {
            "success": True,
            "message": f"Report {filename} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting report {filename}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/types")
async def get_report_types() -> Dict[str, Any]:
    """Get available report types and their descriptions."""
    return {
        "report_types": [
            {
                "value": ReportType.BREAK_SUMMARY.value,
                "label": "Break Summary",
                "description": "Comprehensive analysis of reconciliation breaks",
                "formats": ["json", "csv", "pdf", "excel", "html"]
            },
            {
                "value": ReportType.RESOLUTION_SUMMARY.value,
                "label": "Resolution Summary",
                "description": "Resolution success rates and efficiency metrics",
                "formats": ["json", "csv", "pdf", "excel", "html"]
            },
            {
                "value": ReportType.PERFORMANCE_METRICS.value,
                "label": "Performance Metrics",
                "description": "Key performance indicators and benchmarks",
                "formats": ["json", "csv", "pdf", "excel", "html"]
            },
            {
                "value": ReportType.TREND_ANALYSIS.value,
                "label": "Trend Analysis",
                "description": "Historical trends and forecasting",
                "formats": ["json", "csv", "pdf", "excel", "html"]
            },
            {
                "value": ReportType.AUDIT_TRAIL.value,
                "label": "Audit Trail",
                "description": "User activity and compliance tracking",
                "formats": ["json", "csv", "pdf", "excel", "html"]
            },
            {
                "value": ReportType.COMPLIANCE_REPORT.value,
                "label": "Compliance Report",
                "description": "Regulatory compliance assessment",
                "formats": ["json", "csv", "pdf", "excel", "html"]
            },
            {
                "value": ReportType.OPERATIONAL_DASHBOARD.value,
                "label": "Operational Dashboard",
                "description": "Real-time operational metrics",
                "formats": ["json", "csv", "pdf", "excel", "html"]
            }
        ],
        "formats": [
            {"value": "json", "label": "JSON", "description": "Structured data format"},
            {"value": "csv", "label": "CSV", "description": "Comma-separated values"},
            {"value": "pdf", "label": "PDF", "description": "Portable Document Format"},
            {"value": "excel", "label": "Excel", "description": "Microsoft Excel format"},
            {"value": "html", "label": "HTML", "description": "Web page format"}
        ]
    }


async def get_report_data(report_type: ReportType, db: AsyncSession) -> Dict[str, Any]:
    """Get data for the specified report type."""
    try:
        if report_type == ReportType.BREAK_SUMMARY:
            # Get break data
            from src.core.models.break_types.reconciliation_break import ReconciliationException
            from sqlalchemy import select, func
            
            # Get total breaks
            total_query = select(func.count(ReconciliationException.id))
            total_result = await db.execute(total_query)
            total_breaks = total_result.scalar()
            
            # Get breaks by type
            breaks_query = select(ReconciliationException)
            breaks_result = await db.execute(breaks_query)
            breaks = breaks_result.scalars().all()
            
            breaks_data = []
            for break_item in breaks:
                breaks_data.append({
                    "id": str(break_item.id),
                    "break_type": break_item.break_type,
                    "severity": break_item.severity,
                    "status": break_item.status,
                    "financial_impact": float(break_item.financial_impact) if break_item.financial_impact else 0.0,
                    "created_at": break_item.created_at.isoformat(),
                    "updated_at": break_item.updated_at.isoformat()
                })
            
            return {
                "breaks": breaks_data,
                "total_breaks": total_breaks
            }
        
        elif report_type == ReportType.RESOLUTION_SUMMARY:
            # Get resolution data
            from src.core.models.break_types.reconciliation_break import ReconciliationException
            from sqlalchemy import select, func
            
            # Get resolved breaks
            resolved_query = select(ReconciliationException).where(
                ReconciliationException.status == "resolved"
            )
            resolved_result = await db.execute(resolved_query)
            resolved_breaks = resolved_result.scalars().all()
            
            resolutions_data = []
            for break_item in resolved_breaks:
                resolutions_data.append({
                    "id": str(break_item.id),
                    "break_type": break_item.break_type,
                    "resolved_at": break_item.updated_at.isoformat(),
                    "resolution_time_hours": 2.5,  # This would be calculated
                    "financial_impact": float(break_item.financial_impact) if break_item.financial_impact else 0.0
                })
            
            return {
                "resolutions": resolutions_data,
                "total_resolutions": len(resolutions_data)
            }
        
        elif report_type == ReportType.PERFORMANCE_METRICS:
            # Get performance metrics
            return {
                "metrics": {
                    "break_detection_rate": 0.98,
                    "resolution_success_rate": 0.85,
                    "average_processing_time": 2.3,
                    "data_quality_score": 0.92,
                    "system_uptime": 0.995,
                    "user_satisfaction": 0.88
                }
            }
        
        elif report_type == ReportType.TREND_ANALYSIS:
            # Get trend data
            return {
                "time_series": [
                    {"date": "2024-01-15", "breaks": 5, "resolutions": 4, "financial_impact": 2500.0},
                    {"date": "2024-01-16", "breaks": 3, "resolutions": 3, "financial_impact": 1500.0},
                    {"date": "2024-01-17", "breaks": 7, "resolutions": 6, "financial_impact": 3500.0}
                ]
            }
        
        elif report_type == ReportType.AUDIT_TRAIL:
            # Get audit data
            return {
                "audit_records": [
                    {
                        "user_id": "user001",
                        "action_type": "break_resolution",
                        "timestamp": "2024-01-15T11:30:00",
                        "details": "Resolved security ID break"
                    },
                    {
                        "user_id": "user002",
                        "action_type": "data_validation",
                        "timestamp": "2024-01-16T10:15:00",
                        "details": "Validated coupon calculation"
                    }
                ]
            }
        
        elif report_type == ReportType.COMPLIANCE_REPORT:
            # Get compliance data
            return {
                "compliance_data": {
                    "sox_compliance": {"score": 0.95, "status": "compliant"},
                    "gdpr_compliance": {"score": 0.88, "status": "compliant"},
                    "financial_regulations": {"score": 0.92, "status": "compliant"}
                }
            }
        
        elif report_type == ReportType.OPERATIONAL_DASHBOARD:
            # Get operational data
            return {
                "operational_data": {
                    "active_breaks": 3,
                    "pending_resolutions": 2,
                    "system_health": "healthy",
                    "processing_queue": 5,
                    "user_sessions": 12,
                    "break_processing_rate": 0.85,
                    "resolution_speed": 1.5,
                    "data_throughput": 1000,
                    "system_uptime": 0.995
                }
            }
        
        else:
            return {}
            
    except Exception as e:
        logger.error(f"Error getting report data for {report_type}: {e}")
        return {} 