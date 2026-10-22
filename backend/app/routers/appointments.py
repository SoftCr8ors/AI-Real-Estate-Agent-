"""
Appointments API Router (Phase 5).

Admin endpoints for managing property viewing appointments.
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.appointment import Appointment, AppointmentStatus
from app.services.booking import (
    BookingError,
    cancel_appointment,
    retry_failed_syncs,
    update_appointment_google_sync,
)

router = APIRouter(prefix="/appointments", tags=["appointments"])


# ============================================================================
# SCHEMAS
# ============================================================================

class AppointmentResponse(BaseModel):
    """Appointment response schema"""
    id: int
    lead_id: int
    property_id: int
    scheduled_at: datetime
    duration_minutes: int
    status: str
    notes: str | None
    google_event_id: str | None
    sync_status: str
    sync_error: str | None
    last_sync_attempt: datetime | None
    sync_retry_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class CancelAppointmentRequest(BaseModel):
    """Cancel appointment request"""
    reason: str | None = Field(None, description="Reason for cancellation")


class RetrySyncResponse(BaseModel):
    """Retry sync response"""
    attempted: int
    succeeded: int
    failed: int


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/", response_model=list[AppointmentResponse])
def list_appointments(
    status: AppointmentStatus | None = Query(None, description="Filter by status"),
    sync_status: str | None = Query(None, description="Filter by sync status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[Appointment]:
    """
    List appointments (admin endpoint).

    Args:
        status: Filter by appointment status
        sync_status: Filter by Google sync status (pending, synced, failed)
        limit: Maximum results
        offset: Pagination offset
        db: Database session

    Returns:
        List of appointments
    """
    query = db.query(Appointment)

    if status:
        query = query.filter(Appointment.status == status)

    if sync_status:
        query = query.filter(Appointment.sync_status == sync_status)

    appointments = (
        query
        .order_by(Appointment.scheduled_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return appointments


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
) -> Appointment:
    """
    Get appointment by ID.

    Args:
        appointment_id: Appointment ID
        db: Database session

    Returns:
        Appointment details

    Raises:
        HTTPException: If appointment not found
    """
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()

    if not appointment:
        raise HTTPException(status_code=404, detail=f"Appointment {appointment_id} not found")

    return appointment


@router.post("/{appointment_id}/cancel", response_model=AppointmentResponse)
def cancel_appointment_endpoint(
    appointment_id: int,
    request: CancelAppointmentRequest,
    db: Session = Depends(get_db),
) -> Appointment:
    """
    Cancel an appointment (admin endpoint).

    This also removes the event from Google Calendar if synced.

    Args:
        appointment_id: Appointment ID to cancel
        request: Cancellation request with reason
        db: Database session

    Returns:
        Updated appointment

    Raises:
        HTTPException: If appointment not found
    """
    try:
        appointment = cancel_appointment(
            db=db,
            appointment_id=appointment_id,
            reason=request.reason
        )
        return appointment

    except BookingError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{appointment_id}/retry-sync")
def retry_appointment_sync(
    appointment_id: int,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Manually retry Google Calendar sync for a specific appointment.

    Args:
        appointment_id: Appointment ID
        db: Database session

    Returns:
        Sync result

    Raises:
        HTTPException: If sync fails
    """
    success, message = update_appointment_google_sync(db, appointment_id)

    if success:
        return {"success": True, "message": message}
    else:
        return {"success": False, "message": message}


@router.post("/retry-failed-syncs", response_model=RetrySyncResponse)
def retry_all_failed_syncs(
    db: Session = Depends(get_db),
) -> RetrySyncResponse:
    """
    Retry all appointments with failed Google Calendar sync.

    This endpoint can be called:
    - Manually from admin dashboard
    - Automatically via cron job
    - Via background task

    Args:
        db: Database session

    Returns:
        Retry statistics
    """
    stats = retry_failed_syncs(db)

    return RetrySyncResponse(
        attempted=stats["attempted"],
        succeeded=stats["succeeded"],
        failed=stats["failed"]
    )


@router.get("/stats/summary")
def get_appointment_stats(
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Get appointment statistics.

    Args:
        db: Database session

    Returns:
        Statistics summary
    """
    total = db.query(Appointment).count()
    scheduled = db.query(Appointment).filter(
        Appointment.status == AppointmentStatus.SCHEDULED
    ).count()
    confirmed = db.query(Appointment).filter(
        Appointment.status == AppointmentStatus.CONFIRMED
    ).count()
    completed = db.query(Appointment).filter(
        Appointment.status == AppointmentStatus.COMPLETED
    ).count()
    cancelled = db.query(Appointment).filter(
        Appointment.status == AppointmentStatus.CANCELLED
    ).count()

    sync_pending = db.query(Appointment).filter(
        Appointment.sync_status == "pending"
    ).count()
    sync_failed = db.query(Appointment).filter(
        Appointment.sync_status == "failed"
    ).count()
    sync_synced = db.query(Appointment).filter(
        Appointment.sync_status == "synced"
    ).count()

    return {
        "total": total,
        "by_status": {
            "scheduled": scheduled,
            "confirmed": confirmed,
            "completed": completed,
            "cancelled": cancelled,
        },
        "sync_status": {
            "pending": sync_pending,
            "failed": sync_failed,
            "synced": sync_synced,
        }
    }
