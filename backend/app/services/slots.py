"""
Viewing Slot Generation Service (Phase 5).

Generates available time slots for property viewings with all business rules:
- 45-minute slots from 10:00 to 17:30 in the business timezone (Asia/Dubai)
- At least 1 hour from now
- Next 7 days only
- Removes booked appointments
- Removes blocked times from schedule
- Removes Google Calendar busy times
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.appointment import Appointment, AppointmentStatus
from app.models.property import Property
from app.models.schedule import BlockedTime
from app.services.calendar_google import get_calendar_service

# Business rules
SLOT_DURATION_MINUTES = 45
MIN_ADVANCE_HOURS = 1
MAX_DAYS_AHEAD = 7
WORK_START_HOUR = 10  # 10:00 AM (business timezone)
WORK_END_HOUR = 17  # Last slot: 16:45-17:30
WORK_END_MINUTE = 30


def _ensure_utc(dt: datetime) -> datetime:
    """Treat naive datetimes as UTC and convert aware ones to UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _business_timezone() -> ZoneInfo:
    """Timezone in which viewing hours (10:00-17:30) are defined."""
    try:
        return ZoneInfo(settings.GOOGLE_CALENDAR_TIMEZONE)
    except Exception:
        return ZoneInfo("Asia/Dubai")



def generate_time_slots(
    db: Session,
    property_id: int,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[dict[str, Any]]:
    """
    Generate available viewing slots for a property.

    Args:
        db: Database session
        property_id: Property ID to book viewing for
        start_date: Start date for slots (default: now + 1 hour)
        end_date: End date for slots (default: start + 7 days)

    Returns:
        List of slot dicts with 'start', 'end', 'available' fields

    Raises:
        ValueError: If property not found or not available
    """
    # Verify property exists and is available
    property_obj = db.query(Property).filter(Property.id == property_id).first()
    if not property_obj:
        raise ValueError(f"Property {property_id} not found")

    if property_obj.availability != "available":
        raise ValueError(f"Property {property_id} is not available for viewing")

    # Calculate date range
    now = datetime.now(UTC)
    if start_date is None:
        start_date = now + timedelta(hours=MIN_ADVANCE_HOURS)
    else:
        start_date = _ensure_utc(start_date)
    if end_date is None:
        end_date = start_date + timedelta(days=MAX_DAYS_AHEAD)
    else:
        end_date = _ensure_utc(end_date)

    # Generate all possible slots
    all_slots = _generate_all_slots(start_date, end_date)

    # Filter out past slots (at least 1 hour from now)
    min_start_time = now + timedelta(hours=MIN_ADVANCE_HOURS)
    future_slots = [
        slot for slot in all_slots
        if slot["start"] >= min_start_time
    ]

    # Get booked appointments
    booked_slots = _get_booked_slots(db, start_date, end_date)

    # Get blocked times from schedule
    blocked_slots = _get_blocked_slots(db, start_date, end_date)

    # Get Google Calendar busy times (if available)
    google_busy_slots = _get_google_busy_slots(start_date, end_date)

    # Mark slots as available/unavailable
    available_slots = []
    for slot in future_slots:
        is_available = not (
            _overlaps_with_any(slot, booked_slots)
            or _overlaps_with_any(slot, blocked_slots)
            or _overlaps_with_any(slot, google_busy_slots)
        )

        available_slots.append({
            "start": slot["start"].isoformat(),
            "end": slot["end"].isoformat(),
            "available": is_available
        })

    return available_slots


def _generate_all_slots(
    start_date: datetime,
    end_date: datetime
) -> list[dict[str, datetime]]:
    """
    Generate all possible 45-minute slots within date range.

    Slots are from 10:00 to 17:30 in the business timezone every day
    (last slot: 16:45-17:30).

    Args:
        start_date: Start of date range (UTC)
        end_date: End of date range (UTC)

    Returns:
        List of slot dicts with 'start' and 'end' datetime objects in the
        business timezone
    """
    tz = _business_timezone()
    start_local = start_date.astimezone(tz)
    end_local = end_date.astimezone(tz)

    slots = []
    current_date = start_local.replace(hour=0, minute=0, second=0, microsecond=0)

    while current_date.date() <= end_local.date():
        # Generate slots for this day (10:00 to 17:30)
        slot_time = current_date.replace(hour=WORK_START_HOUR, minute=0)

        while slot_time.hour < WORK_END_HOUR or (
            slot_time.hour == WORK_END_HOUR and slot_time.minute == 0
        ):
            slot_end = slot_time + timedelta(minutes=SLOT_DURATION_MINUTES)

            # Don't create slots that end after 17:30
            if slot_end.hour > WORK_END_HOUR or (
                slot_end.hour == WORK_END_HOUR and slot_end.minute > WORK_END_MINUTE
            ):
                break

            slots.append({
                "start": slot_time,
                "end": slot_end
            })

            # Move to next slot (45 minutes later)
            slot_time = slot_end

        # Move to next day
        current_date += timedelta(days=1)

    return slots


def _get_booked_slots(
    db: Session,
    start_date: datetime,
    end_date: datetime
) -> list[dict[str, datetime]]:
    """
    Get all booked appointment slots in date range.

    Args:
        db: Database session
        start_date: Start of date range
        end_date: End of date range

    Returns:
        List of slot dicts with 'start' and 'end' datetime objects
    """
    # Query appointments that are scheduled or confirmed (not cancelled/no-show)
    appointments = db.query(Appointment).filter(
        and_(
            Appointment.scheduled_at >= start_date,
            Appointment.scheduled_at < end_date,
            Appointment.status.in_([
                AppointmentStatus.SCHEDULED,
                AppointmentStatus.CONFIRMED,
                AppointmentStatus.COMPLETED
            ])
        )
    ).all()

    slots = []
    for apt in appointments:
        apt_start = _ensure_utc(apt.scheduled_at)
        slots.append({
            "start": apt_start,
            "end": apt_start + timedelta(minutes=apt.duration_minutes)
        })

    return slots


def _get_blocked_slots(
    db: Session,
    start_date: datetime,
    end_date: datetime
) -> list[dict[str, datetime]]:
    """
    Get blocked time slots from blocked_times table.

    Args:
        db: Database session
        start_date: Start of date range
        end_date: End of date range

    Returns:
        List of slot dicts with 'start' and 'end' datetime objects
    """
    # Query blocked times in date range
    blocked_times = db.query(BlockedTime).filter(
        and_(
            BlockedTime.date >= start_date.date(),
            BlockedTime.date <= end_date.date()
        )
    ).all()

    slots = []
    for block in blocked_times:
        # Blocked times are wall-clock times in the business timezone
        block_start = datetime.combine(
            block.date, block.start_time, tzinfo=_business_timezone()
        )
        block_end = datetime.combine(
            block.date, block.end_time, tzinfo=_business_timezone()
        )

        slots.append({
            "start": block_start,
            "end": block_end
        })

    return slots


def _get_google_busy_slots(
    start_date: datetime,
    end_date: datetime
) -> list[dict[str, datetime]]:
    """
    Get busy time slots from Google Calendar.

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        List of slot dicts with 'start' and 'end' datetime objects
        Empty list if Google Calendar not configured

    Raises:
        RuntimeError: If the calendar is configured but cannot be reached.
            Callers must fail closed (show no slots) instead of risking a
            double-booking on an availability we could not verify.
    """
    calendar_service = get_calendar_service()

    # If Google Calendar not configured, return empty list
    if not calendar_service.is_available():
        return []

    try:
        # Get busy times from Google Calendar
        busy_times = calendar_service.get_busy_times(start_date, end_date)

        # Convert to slot format
        slots = []
        for start, end in busy_times:
            slots.append({
                "start": _ensure_utc(start),
                "end": _ensure_utc(end)
            })

        return slots

    except Exception as e:
        raise RuntimeError(f"Google Calendar unavailable: {e}") from e


def _overlaps_with_any(
    slot: dict[str, datetime],
    other_slots: list[dict[str, datetime]]
) -> bool:
    """
    Check if a slot overlaps with any slot in a list.

    Two slots overlap if one starts before the other ends.

    Args:
        slot: Slot to check
        other_slots: List of slots to check against

    Returns:
        True if slot overlaps with any other slot
    """
    for other in other_slots:
        # Overlap if slot starts before other ends AND slot ends after other starts
        if slot["start"] < other["end"] and slot["end"] > other["start"]:
            return True

    return False


def check_slot_available(
    db: Session,
    property_id: int,
    slot_start: datetime,
    slot_duration_minutes: int = SLOT_DURATION_MINUTES
) -> tuple[bool, str | None]:
    """
    Check if a specific slot is available for booking.

    This is used during booking to re-verify availability.

    Args:
        db: Database session
        property_id: Property ID
        slot_start: Slot start time
        slot_duration_minutes: Slot duration in minutes

    Returns:
        Tuple of (is_available, error_message)
    """
    slot_start = _ensure_utc(slot_start)
    slot_end = slot_start + timedelta(minutes=slot_duration_minutes)

    # Check property is available
    property_obj = db.query(Property).filter(Property.id == property_id).first()
    if not property_obj:
        return False, f"Property {property_id} not found"

    if property_obj.availability != "available":
        return False, f"Property {property_id} is not available for viewing"

    # Check slot is in the future (at least 1 hour from now)
    now = datetime.now(UTC)
    min_start_time = now + timedelta(hours=MIN_ADVANCE_HOURS)
    if slot_start < min_start_time:
        return False, "Slot must be at least 1 hour in the future"

    # Check slot is within max days ahead
    max_date = now + timedelta(days=MAX_DAYS_AHEAD)
    if slot_start > max_date:
        return False, f"Slot must be within {MAX_DAYS_AHEAD} days"

    # Check slot is within working hours (working hours are business-local)
    local_start = slot_start.astimezone(_business_timezone())
    local_end = slot_end.astimezone(_business_timezone())
    if (local_start.hour < WORK_START_HOUR or
        local_start.hour > WORK_END_HOUR or
        (local_start.hour == WORK_END_HOUR and local_start.minute > 0)):
        return False, f"Slot must be between {WORK_START_HOUR}:00 and {WORK_END_HOUR}:30"

    if (local_end.hour > WORK_END_HOUR or
        (local_end.hour == WORK_END_HOUR and local_end.minute > WORK_END_MINUTE)):
        return False, f"Slot must end by {WORK_END_HOUR}:{WORK_END_MINUTE:02d}"

    # Check no overlapping appointments
    overlapping_appointments = db.query(Appointment).filter(
        and_(
            # Overlap check: appointment starts before slot ends AND appointment ends after slot starts
            Appointment.scheduled_at < slot_end,
            Appointment.scheduled_at >= slot_start - timedelta(minutes=SLOT_DURATION_MINUTES),
            Appointment.status.in_([
                AppointmentStatus.SCHEDULED,
                AppointmentStatus.CONFIRMED,
                AppointmentStatus.COMPLETED
            ])
        )
    ).first()

    if overlapping_appointments:
        return False, "Slot is already booked"

    # Check no blocked times (blocked times are business-local wall times)
    slot_date = local_start.date()
    blocked_times = db.query(BlockedTime).filter(
        and_(
            BlockedTime.date == slot_date,
            BlockedTime.start_time < local_end.time(),
            BlockedTime.end_time > local_start.time()
        )
    ).first()

    if blocked_times:
        return False, "Slot is blocked"

    # Check Google Calendar (if available). Fail closed: if the calendar cannot
    # be reached we cannot prove the slot is free, so refuse the booking.
    calendar_service = get_calendar_service()
    if calendar_service.is_available():
        try:
            busy_times = calendar_service.get_busy_times(slot_start, slot_end)
            if busy_times:
                return False, "Slot conflicts with Google Calendar"
        except Exception as e:
            return False, f"Unable to verify calendar availability: {e}"

    return True, None
