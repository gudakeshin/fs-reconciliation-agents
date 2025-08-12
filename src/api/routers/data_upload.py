"""
Data Upload Router for FS Reconciliation Agents API.

This module provides API endpoints for file upload and data ingestion,
including support for various file formats and data processing.
"""

import logging
import os
import asyncio
from uuid import uuid4
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.agents.data_ingestion.agent import process_financial_file
from src.core.services.data_services.database import get_db_session
from src.core.utils.security_utils.authentication import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/data", tags=["data"])

# In-memory job store for async processing
JOBS: Dict[str, Dict[str, Any]] = {}
RECONCILE_JOBS: Dict[str, Dict[str, Any]] = {}

# Supported file types
SUPPORTED_EXTENSIONS = {'.csv', '.xlsx', '.xls', '.xml', '.pdf', '.txt'}

# Upload directory
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    data_source: str = Form("unknown"),
    file_type: str = Form(None),
    processing_options: Dict[str, Any] = Form({}),
    db: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """Upload and enqueue processing of a financial data file (async)."""
    try:
        # Validate file type
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Supported types: {', '.join(SUPPORTED_EXTENSIONS)}"
            )
        
        # Create unique filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file.filename.replace(' ', '_')}"
        file_path = UPLOAD_DIR / safe_filename
        
        # Save uploaded file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.info(f"File uploaded: {file_path}")

        # Enqueue async processing and return job id immediately
        job_id = str(uuid4())
        JOBS[job_id] = {
            "status": "queued",
            "created_at": datetime.utcnow().isoformat(),
            "file_path": str(file_path),
            "data_source": data_source,
        }

        async def _run_job(job: str, path: str, source: str):
            try:
                JOBS[job]["status"] = "processing"
                result = await process_financial_file(path, source)
                JOBS[job]["status"] = "completed" if result.get("success") else "failed"
                JOBS[job]["result"] = result
                JOBS[job]["completed_at"] = datetime.utcnow().isoformat()
            except Exception as e:
                logger.error(f"Async job {job} failed: {e}")
                JOBS[job]["status"] = "failed"
                JOBS[job]["error"] = str(e)
                JOBS[job]["completed_at"] = datetime.utcnow().isoformat()

        asyncio.create_task(_run_job(job_id, str(file_path), data_source))

        # 202 Accepted with job reference
        return {
            "success": True,
            "accepted": True,
            "job_id": job_id,
            "message": "File accepted for processing",
            "file_path": str(file_path)
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/upload/job/{job_id}")
async def get_upload_job(job_id: str) -> Dict[str, Any]:
    """Get status/result for an upload processing job."""
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"success": True, **job}


@router.get("/upload/jobs")
async def list_upload_jobs() -> Dict[str, Any]:
    """List current upload jobs (non-persistent)."""
    return {"success": True, "jobs": JOBS}


def _load_csv_records(file_path: str) -> List[Dict[str, Any]]:
    import pandas as pd
    df = pd.read_csv(file_path, encoding='utf-8-sig')
    records = df.to_dict('records')
    normalized: List[Dict[str, Any]] = []
    for row in records:
        new_row: Dict[str, Any] = {}
        for k, v in row.items():
            key = (k or "").strip().lower().replace(" ", "_").replace("-", "_")
            if key in ("transactionid", "transaction_id", "externalid"):
                key = "external_id"
            elif key in ("securityid", "security_id"):
                key = "security_id"
            elif key in ("qty", "quantity"):
                key = "quantity"
            elif key in ("price", "amount", "notional"):
                key = "amount"
            elif key in ("ccy", "currency"):
                key = "currency"
            elif key in ("tradedate", "trade_date"):
                key = "trade_date"
            elif key in ("settlementdate", "settlement_date"):
                key = "settlement_date"
            new_row[key] = v
        normalized.append(new_row)
    return normalized


@router.post("/reconcile/start")
async def start_reconciliation(
    job_id_a: str = Form(...),
    job_id_b: str = Form(...),
    db: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """Start reconciliation between two uploaded files by job ids."""
    if job_id_a not in JOBS or job_id_b not in JOBS:
        raise HTTPException(status_code=400, detail="Invalid job ids; data missing")
    file_a = JOBS[job_id_a].get("file_path")
    file_b = JOBS[job_id_b].get("file_path")
    if not file_a or not file_b:
        raise HTTPException(status_code=400, detail="Data missing for reconciliation")

    recon_id = str(uuid4())
    RECONCILE_JOBS[recon_id] = {
        "status": "queued",
        "created_at": datetime.utcnow().isoformat(),
        "file_a": file_a,
        "file_b": file_b,
    }

    async def _run_reconcile(job_id: str, path_a: str, path_b: str):
        from src.core.agents.matching.agent import match_financial_transactions
        from src.core.agents.exception_identification.agent import identify_reconciliation_exceptions
        from src.core.agents.resolution_engine.agent import resolve_reconciliation_exceptions
        from src.core.agents.reporting.agent import generate_reconciliation_report
        from src.core.agents.human_in_loop.agent import human_in_loop_review
        
        try:
            RECONCILE_JOBS[job_id]["status"] = "processing"
            RECONCILE_JOBS[job_id]["progress"] = "Starting reconciliation..."
            
            # Load data
            tx_a = _load_csv_records(path_a)
            tx_b = _load_csv_records(path_b)
            
            # Step 1: Matching Agent
            RECONCILE_JOBS[job_id]["progress"] = "Running matching agent..."
            match_result = await match_financial_transactions(tx_a, tx_b)
            if not match_result.get("success"):
                RECONCILE_JOBS[job_id]["status"] = "failed"
                RECONCILE_JOBS[job_id]["error"] = match_result.get("error", "Matching failed")
                RECONCILE_JOBS[job_id]["result"] = match_result
                RECONCILE_JOBS[job_id]["completed_at"] = datetime.utcnow().isoformat()
                return

            # Step 2: Exception Identification Agent
            RECONCILE_JOBS[job_id]["progress"] = "Running exception identification agent..."
            exceptions_result = await identify_reconciliation_exceptions(
                transactions=tx_a + tx_b,
                matches=match_result.get("matches", [])
            )

            # Step 3: Resolution Engine Agent
            RECONCILE_JOBS[job_id]["progress"] = "Running resolution engine agent..."
            resolution_result = await resolve_reconciliation_exceptions(
                exceptions_result.get("exceptions", [])
            )

            # Step 4: Reporting Agent
            RECONCILE_JOBS[job_id]["progress"] = "Generating reconciliation report..."
            reporting_result = await generate_reconciliation_report(
                match_result=match_result,
                exceptions_result=exceptions_result,
                resolution_result=resolution_result
            )

            # Step 5: Human-in-Loop Review Agent
            RECONCILE_JOBS[job_id]["progress"] = "Running human-in-loop review..."
            human_review_result = await human_in_loop_review(
                exceptions=exceptions_result.get("exceptions", []),
                resolutions=resolution_result.get("proposed_actions", [])
            )

            RECONCILE_JOBS[job_id]["status"] = "completed"
            RECONCILE_JOBS[job_id]["result"] = {
                "matching": match_result,
                "exceptions": exceptions_result,
                "resolution": resolution_result,
                "reporting": reporting_result,
                "human_review": human_review_result,
            }
            RECONCILE_JOBS[job_id]["completed_at"] = datetime.utcnow().isoformat()
        except Exception as e:
            logger.error(f"Reconciliation job {job_id} failed: {e}")
            RECONCILE_JOBS[job_id]["status"] = "failed"
            RECONCILE_JOBS[job_id]["error"] = str(e)
            RECONCILE_JOBS[job_id]["completed_at"] = datetime.utcnow().isoformat()

    asyncio.create_task(_run_reconcile(recon_id, file_a, file_b))
    return {"success": True, "accepted": True, "reconcile_job_id": recon_id}


@router.get("/reconcile/job/{reconcile_job_id}")
async def get_reconcile_job(reconcile_job_id: str) -> Dict[str, Any]:
    job = RECONCILE_JOBS.get(reconcile_job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"success": True, **job}


@router.post("/upload/batch")
async def upload_multiple_files(
    files: List[UploadFile] = File(...),
    data_source: str = Form("unknown"),
    processing_options: Dict[str, Any] = Form({}),
    db: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """Upload and process multiple financial data files."""
    try:
        results = []
        total_processed = 0
        total_errors = 0
        
        for file in files:
            try:
                # Validate file type
                file_extension = Path(file.filename).suffix.lower()
                if file_extension not in SUPPORTED_EXTENSIONS:
                    results.append({
                        "filename": file.filename,
                        "success": False,
                        "error": f"Unsupported file type: {file_extension}"
                    })
                    total_errors += 1
                    continue
                
                # Create unique filename
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                safe_filename = f"{timestamp}_{file.filename.replace(' ', '_')}"
                file_path = UPLOAD_DIR / safe_filename
                
                # Save uploaded file
                with open(file_path, "wb") as buffer:
                    content = await file.read()
                    buffer.write(content)
                
                # Process file
                result = await process_financial_file(str(file_path), data_source)
                
                if result.get("success"):
                    results.append({
                        "filename": file.filename,
                        "success": True,
                        "processed_records": result.get("processed_records", 0),
                        "processing_time_ms": result.get("processing_time_ms", 0)
                    })
                    total_processed += result.get("processed_records", 0)
                else:
                    results.append({
                        "filename": file.filename,
                        "success": False,
                        "error": "Processing failed",
                        "validation_errors": result.get("validation_errors", [])
                    })
                    total_errors += 1
                    
            except Exception as e:
                logger.error(f"Error processing file {file.filename}: {e}")
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "error": str(e)
                })
                total_errors += 1
        
        return {
            "success": total_errors == 0,
            "total_files": len(files),
            "successful_files": len([r for r in results if r["success"]]),
            "failed_files": total_errors,
            "total_processed_records": total_processed,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error in batch upload: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/upload/status")
async def get_upload_status(
    db: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get upload processing status and statistics."""
    try:
        # Get recent uploads from database (this would be implemented based on your audit trail)
        recent_uploads = []
        
        # Get file system statistics
        upload_files = list(UPLOAD_DIR.glob("*"))
        total_files = len(upload_files)
        total_size = sum(f.stat().st_size for f in upload_files)
        
        # Get processing statistics
        processing_stats = {
            "total_uploads": total_files,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "recent_uploads": recent_uploads,
            "supported_formats": list(SUPPORTED_EXTENSIONS),
            "upload_directory": str(UPLOAD_DIR)
        }
        
        return processing_stats
        
    except Exception as e:
        logger.error(f"Error getting upload status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/upload/{filename}")
async def delete_uploaded_file(
    filename: str,
    db: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """Delete an uploaded file."""
    try:
        file_path = UPLOAD_DIR / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        # Check if file is in upload directory (security check)
        if not file_path.resolve().is_relative_to(UPLOAD_DIR.resolve()):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Delete file
        file_path.unlink()
        
        return {
            "success": True,
            "message": f"File {filename} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file {filename}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/upload/supported-formats")
async def get_supported_formats() -> Dict[str, Any]:
    """Get supported file formats and their descriptions."""
    return {
        "supported_formats": [
            {
                "extension": ".csv",
                "description": "Comma-separated values file",
                "mime_type": "text/csv",
                "max_size_mb": 100
            },
            {
                "extension": ".xlsx",
                "description": "Microsoft Excel file (2007+)",
                "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "max_size_mb": 50
            },
            {
                "extension": ".xls",
                "description": "Microsoft Excel file (legacy)",
                "mime_type": "application/vnd.ms-excel",
                "max_size_mb": 50
            },
            {
                "extension": ".xml",
                "description": "XML data file",
                "mime_type": "application/xml",
                "max_size_mb": 100
            },
            {
                "extension": ".pdf",
                "description": "Portable Document Format",
                "mime_type": "application/pdf",
                "max_size_mb": 50
            },
            {
                "extension": ".txt",
                "description": "Text file (SWIFT messages)",
                "mime_type": "text/plain",
                "max_size_mb": 100
            }
        ],
        "upload_directory": str(UPLOAD_DIR),
        "max_file_size_mb": 100
    }


@router.post("/validate")
async def validate_file_format(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """Validate file format and structure without processing."""
    try:
        # Validate file type
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in SUPPORTED_EXTENSIONS:
            return {
                "valid": False,
                "error": f"Unsupported file type: {file_extension}",
                "supported_types": list(SUPPORTED_EXTENSIONS)
            }
        
        # Read file content for validation
        content = await file.read()
        
        # Basic validation based on file type
        validation_result = {
            "valid": True,
            "filename": file.filename,
            "file_size": len(content),
            "file_type": file_extension,
            "validation_details": {}
        }
        
        if file_extension == ".csv":
            # Validate CSV structure
            lines = content.decode('utf-8').split('\n')
            if len(lines) < 2:
                validation_result["valid"] = False
                validation_result["error"] = "CSV file must have at least header and one data row"
            else:
                validation_result["validation_details"] = {
                    "total_rows": len(lines),
                    "has_header": True,
                    "estimated_columns": len(lines[0].split(','))
                }
        
        elif file_extension in [".xlsx", ".xls"]:
            # Basic Excel validation
            validation_result["validation_details"] = {
                "file_size_mb": round(len(content) / (1024 * 1024), 2),
                "is_excel": True
            }
        
        elif file_extension == ".xml":
            # Basic XML validation
            try:
                import xml.etree.ElementTree as ET
                ET.fromstring(content)
                validation_result["validation_details"] = {
                    "xml_valid": True,
                    "file_size_mb": round(len(content) / (1024 * 1024), 2)
                }
            except ET.ParseError:
                validation_result["valid"] = False
                validation_result["error"] = "Invalid XML format"
        
        elif file_extension == ".pdf":
            # Basic PDF validation
            if not content.startswith(b'%PDF'):
                validation_result["valid"] = False
                validation_result["error"] = "Invalid PDF format"
            else:
                validation_result["validation_details"] = {
                    "pdf_valid": True,
                    "file_size_mb": round(len(content) / (1024 * 1024), 2)
                }
        
        elif file_extension == ".txt":
            # Basic text file validation
            validation_result["validation_details"] = {
                "total_lines": len(content.decode('utf-8').split('\n')),
                "file_size_mb": round(len(content) / (1024 * 1024), 2)
            }
        
        return validation_result
        
    except Exception as e:
        logger.error(f"Error validating file: {e}")
        return {
            "valid": False,
            "error": f"Validation error: {str(e)}"
        } 