"""
Export routes for generating and downloading attendance reports.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io

from app.database import get_db
from app.models import AuditLog
from app.schemas import ExportRequest
from app.services.attendance_service import AttendanceService
from app.services.export_service import get_export_service
from app.utils.security import get_current_user, get_client_ip, require_role
from app.utils.logging import get_logger

router = APIRouter(prefix="/api/export", tags=["Export"])
logger = get_logger()


@router.post("/generate")
async def generate_export(
    request: Request,
    export_request: ExportRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin", "hr"))
):
    attendance_service = AttendanceService(db)
    records = attendance_service.get_attendance_records(
        start_date=export_request.start_date,
        end_date=export_request.end_date,
        include_unrecognized=export_request.include_unrecognized,
        limit=10000
    )

    if not records:
        raise HTTPException(status_code=404, detail="No records found for the specified date range")

    export_service = get_export_service()

    if export_request.format == "xlsx":
        file_bytes, filename = export_service.export_to_excel(
            records,
            export_request.start_date,
            export_request.end_date,
            save_to_disk=True
        )
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        file_bytes, filename = export_service.export_to_csv(
            records,
            export_request.start_date,
            export_request.end_date,
            save_to_disk=True
        )
        media_type = "text/csv"

    audit_log = AuditLog(
        admin_user=current_user["username"],
        action="export_attendance",
        resource_type="export",
        details={
            "start_date": export_request.start_date,
            "end_date": export_request.end_date,
            "format": export_request.format,
            "record_count": len(records),
            "filename": filename
        },
        ip_address=get_client_ip(request)
    )
    db.add(audit_log)
    db.commit()

    logger.info(f"Export generated: {filename} ({len(records)} records)")

    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/list")
async def list_exports(
    current_user: dict = Depends(require_role("admin", "hr"))
):
    export_service = get_export_service()
    exports = export_service.list_exports()
    return {"exports": exports}


@router.get("/download/{filename}")
async def download_export(
    filename: str,
    current_user: dict = Depends(require_role("admin", "hr"))
):
    export_service = get_export_service()
    file_path = export_service.get_export_file(filename)

    if not file_path:
        raise HTTPException(status_code=404, detail="Export file not found")

    if filename.endswith('.xlsx'):
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        media_type = "text/csv"

    with open(file_path, 'rb') as f:
        file_bytes = f.read()

    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.delete("/{filename}")
async def delete_export(
    request: Request,
    filename: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin", "hr"))
):
    export_service = get_export_service()
    success = export_service.delete_export(filename)

    if not success:
        raise HTTPException(status_code=404, detail="Export file not found")

    audit_log = AuditLog(
        admin_user=current_user["username"],
        action="delete_export",
        resource_type="export",
        details={"filename": filename},
        ip_address=get_client_ip(request)
    )
    db.add(audit_log)
    db.commit()

    logger.info(f"Export deleted: {filename}")
    return {"message": "Export deleted successfully"}
