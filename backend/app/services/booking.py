"""
Viewing Booking Service (Phase 5).

Handles atomic appointment booking with:
- Re-validation of property and slot availability
- Transaction safety (appointment saved even if Google sync fails)
- Automatic Google Calendar sync with retry mechanism
- Lead status progression to "Viewing Scheduled"
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.appointment import Appointment, AppointmentStatus
from app.models.lead import Lead, LeadStatus
from app.models.property import Property
from app.services.calendar_google import get_calendar_service
from app.services.slots import SLOT_DURATION_MINUTES, check_slot_available


class BookingError(Exception):
    """Raised when booking fails"""
    pass


def book_viewing(
    db: Session,
    lead_id: int,
    property_id: int,
    scheduled_at: datetime,
    duration_minutes: int = SLOT_DURATION_MINUTES,
    notes: str | None = None
) -> Appointment:
    """
    Book a property viewing appointment with atomic transaction.

    Process:
    1. Verify customer has name + contact (phone or email)
    2. Re-check property is available
    3. Re-check slot is available (prevents double booking)
    4. Create appointment in database (ALWAYS saved, even if Google fails)
    5. Update lead status to "Viewing Scheduled"
    6. Try to create Google Calendar event
    7. If Google fails, mark sync_status as "failed" for retry

    Args:
        db: Database session
        lead_id: Lead ID
        property_id: Property ID
        scheduled_at: Appointment start time
        duration_minutes: Appointment duration (default 45 minutes)
        notes: Optional notes

    Returns:
        Created Appointment object

    Raises:
        BookingError: If booking validation fails
    """
    # 1. Verify lead exists and has required contact info
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise BookingError(f"Lead {lead_id} not found")

    if not lead.customer_id:
        raise BookingError("Customer information required for booking")

    # Check customer has name and contact (from conversation customer_state)
    customer = lead.customer
    if not customer:
        raise BookingError("Customer not found")

    # Customer needs name and at least phone or email
    if not customer.name:
        raise BookingError("Customer name required for booking")

    if not customer.phone and not customer.email:
        raise BookingError("Customer phone or email required for booking")

    # 2. Re-check property is available
    property_obj = db.query(Property).filter(Property.id == property_id).first()
    if not property_obj:
        raise BookingError(f"Property {property_id} not found")

    if property_obj.availability != "available":
        raise BookingError(f"Property {property_id} is not available for viewing")

    # 3. Re-check slot is available (critical: prevents double booking)
    is_available, error_msg = check_slot_available(
        db=db,
        property_id=property_id,
        slot_start=scheduled_at,
        slot_duration_minutes=duration_minutes
    )

    if not is_available:
        raise BookingError(f"Slot not available: {error_msg}")

    # 4. Create appointment in database (transaction starts here)
    appointment = Appointment(
        lead_id=lead_id,
        property_id=property_id,
        scheduled_at=scheduled_at,
        duration_minutes=duration_minutes,
        status=AppointmentStatus.SCHEDULED,
        notes=notes,
        sync_status="pending",  # Will try to sync with Google Calendar
        sync_retry_count=0
    )

    db.add(appointment)
    db.flush()  # Get appointment.id without committing

    # 5. Update lead status to "Viewing Scheduled"
    if lead.status != LeadStatus.VIEWING_SCHEDULED:
        from app.services.lead_status import update_lead_status

        update_lead_status(
            db=db,
            lead_id=lead_id,
            new_status=LeadStatus.VIEWING_SCHEDULED,
            reason=f"Viewing booked for property {property_id}",
            automated=True
        )

    # Commit transaction (appointment and lead update saved)
    db.commit()
    db.refresh(appointment)

    # 6. Try to create Google Calendar event (outside transaction)
    _sync_appointment_to_google(db, appointment)

    return appointment


def _sync_appointment_to_google(
    db: Session,
    appointment: Appointment,
    retry: bool = False
) -> bool:
    """
    Sync appointment to Google Calendar.

    This happens AFTER the appointment is saved in database, so if Google fails,
    the appointment still exists and can be retried later.

    Args:
        db: Database session
        appointment: Appointment to sync
        retry: Whether this is a retry attempt

    Returns:
        True if sync succeeded, False if failed
    """
    calendar_service = get_calendar_service()

    # If Google Calendar not configured, mark as failed (manual calendar entry needed)
    if not calendar_service.is_available():
        appointment.sync_status = "failed"
        appointment.sync_error = "Google Calendar not configured"
        appointment.last_sync_attempt = datetime.now()
        db.commit()
        return False

    try:
        # Build event details
        property_obj = appointment.property
        lead = appointment.lead
        customer = lead.customer if lead else None

        summary = f"Property Viewing: {property_obj.title}"

        description_parts = [
            f"Property: {property_obj.title}",
            f"Type: {property_obj.property_type}",
            f"Location: {property_obj.location}",
        ]

        if customer:
            description_parts.append(f"\nCustomer: {customer.name}")
            if customer.phone:
                description_parts.append(f"Phone: {customer.phone}")
            if customer.email:
                description_parts.append(f"Email: {customer.email}")

        if appointment.notes:
            description_parts.append(f"\nNotes: {appointment.notes}")

        description = "\n".join(description_parts)

        location = property_obj.location

        # Service accounts cannot invite attendees - customer info is in description
        # Customer will receive SMS/email confirmation instead (Phase 6)
        attendees = None

        # Create Google Calendar event
        event_id = calendar_service.create_event(
            summary=summary,
            start_datetime=appointment.scheduled_at,
            end_datetime=appointment.scheduled_at + timedelta(minutes=appointment.duration_minutes),
            description=description,
            location=location,
            attendees=attendees
        )

        # Update appointment with Google event info
        appointment.google_event_id = event_id
        appointment.google_calendar_id = settings.GOOGLE_CALENDAR_ID
        appointment.sync_status = "synced"
        appointment.sync_error = None
        appointment.last_sync_attempt = datetime.now()
        db.commit()

        return True

    except Exception as e:
        # Google Calendar sync failed - mark for retry
        error_message = str(e)
        appointment.sync_status = "failed"
        appointment.sync_error = error_message[:500]  # Limit error message length
        appointment.last_sync_attempt = datetime.now()

        if retry:
            appointment.sync_retry_count += 1

        db.commit()

        print(f"Failed to sync appointment {appointment.id} to Google Calendar: {e}")
        return False


def retry_failed_syncs(db: Session, max_retries: int | None = None) -> dict[str, int]:
    """
    Retry syncing appointments that failed Google Calendar sync.

    This can be called:
    - Automatically via background task
    - Manually from admin dashboard
    - Via cron job

    Args:
        db: Database session
        max_retries: Override default max retries from config

    Returns:
        Dict with counts: {"attempted": N, "succeeded": N, "failed": N}
    """
    if max_retries is None:
        max_retries = settings.GOOGLE_CALENDAR_RETRY_MAX

    # Find appointments that need retry
    appointments_to_retry = db.query(Appointment).filter(
        Appointment.sync_status == "failed",
        Appointment.sync_retry_count < max_retries,
        Appointment.status.in_([
            AppointmentStatus.SCHEDULED,
            AppointmentStatus.CONFIRMED
        ])
    ).all()

    stats = {
        "attempted": 0,
        "succeeded": 0,
        "failed": 0
    }

    for appointment in appointments_to_retry:
        stats["attempted"] += 1

        success = _sync_appointment_to_google(db, appointment, retry=True)

        if success:
            stats["succeeded"] += 1
        else:
            stats["failed"] += 1

    return stats


def cancel_appointment(
    db: Session,
    appointment_id: int,
    reason: str | None = None
) -> Appointment:
    """
    Cancel an appointment (admin only).

    Process:
    1. Set appointment status to CANCELLED
    2. Delete Google Calendar event (if synced)
    3. Update lead status if needed

    Args:
        db: Database session
        appointment_id: Appointment ID to cancel
        reason: Cancellation reason (optional)

    Returns:
        Updated Appointment object

    Raises:
        BookingError: If appointment not found
    """
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise BookingError(f"Appointment {appointment_id} not found")

    # Update appointment status
    appointment.status = AppointmentStatus.CANCELLED

    if reason:
        appointment.notes = f"{appointment.notes or ''}\nCancellation reason: {reason}".strip()

    # Try to delete Google Calendar event
    if appointment.google_event_id and appointment.sync_status == "synced":
        calendar_service = get_calendar_service()

        if calendar_service.is_available():
            try:
                calendar_service.delete_event(appointment.google_event_id)
                appointment.sync_status = "synced"  # Still synced (deleted)
            except Exception as e:
                # Log error but don't fail cancellation
                print(f"Failed to delete Google Calendar event: {e}")
                appointment.sync_error = f"Failed to delete from calendar: {str(e)[:500]}"

    db.commit()
    db.refresh(appointment)

    return appointment


def update_appointment_google_sync(
    db: Session,
    appointment_id: int
) -> tuple[bool, str]:
    """
    Manually trigger Google Calendar sync for an appointment.

    Used from admin dashboard to retry failed syncs.

    Args:
        db: Database session
        appointment_id: Appointment ID

    Returns:
        Tuple of (success, message)
    """
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        return False, f"Appointment {appointment_id} not found"

    if appointment.status == AppointmentStatus.CANCELLED:
        return False, "Cannot sync cancelled appointment"

    success = _sync_appointment_to_google(db, appointment, retry=True)

    if success:
        return True, "Successfully synced to Google Calendar"
    else:
        return False, f"Sync failed: {appointment.sync_error}"
