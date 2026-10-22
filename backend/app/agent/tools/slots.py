"""
Get available viewing slots tool.
AI agent uses this to check available appointment times.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.schemas.tools import GetAvailableSlotsOutput, TimeSlot
from app.services.slots import MAX_DAYS_AHEAD, generate_time_slots

# ============================================================================
# TOOL DEFINITION
# ============================================================================

TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "get_available_slots",
        "description": (
            "Get available viewing time slots for a property. "
            "Use this when customer wants to schedule a viewing or asks about available times."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "property_id": {
                    "type": "integer",
                    "description": "The property ID to check viewing slots for",
                },
                "date_from": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format",
                },
                "date_to": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format",
                },
            },
            "required": ["property_id", "date_from", "date_to"],
        },
    },
}


# ============================================================================
# TOOL EXECUTION
# ============================================================================

def get_available_slots_tool(
    db: Session,
    params: dict[str, Any],
) -> GetAvailableSlotsOutput:
    """
    Execute viewing slots retrieval.

    Args:
        db: Database session
        params: Parameters from AI (property_id, date_from, date_to)

    Returns:
        GetAvailableSlotsOutput with available time slots

    Raises:
        ValueError: If property not found or not available
    """
    # Extract and validate parameters
    property_id = params.get("property_id")
    date_from_str = params.get("date_from")
    date_to_str = params.get("date_to")

    if not property_id:
        raise ValueError("property_id is required")
    if not date_from_str:
        raise ValueError("date_from is required")
    if not date_to_str:
        raise ValueError("date_to is required")

    # Parse dates (interpreted as UTC calendar days)
    try:
        start_date = datetime.strptime(date_from_str, "%Y-%m-%d").replace(tzinfo=UTC)
        end_date = datetime.strptime(date_to_str, "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError as e:
        raise ValueError(f"Invalid date format. Use YYYY-MM-DD: {e}") from e

    # date_to is inclusive, so the generation range ends at the next midnight
    end_date = end_date + timedelta(days=1)

    # Recommend only what can actually be booked right now: at least 1 hour
    # ahead (enforced by the service) and no more than MAX_DAYS_AHEAD out.
    now = datetime.now(UTC)
    start_date = max(start_date, now)
    end_date = min(end_date, now + timedelta(days=MAX_DAYS_AHEAD))
    if end_date <= start_date:
        return GetAvailableSlotsOutput(property_id=property_id, slots=[])

    # Generate real slots. The service raises RuntimeError if the calendar is
    # configured but unreachable; fail closed by returning no slots so the AI
    # offers a human consultant instead of guessing.
    try:
        slot_dicts = generate_time_slots(
            db=db,
            property_id=property_id,
            start_date=start_date,
            end_date=end_date
        )
    except RuntimeError:
        return GetAvailableSlotsOutput(property_id=property_id, slots=[])

    # Convert to TimeSlot schema objects (max 10 so the reply stays readable)
    available_slots: list[TimeSlot] = []
    for slot in slot_dicts:
        if not slot["available"]:
            continue

        slot_dt = datetime.fromisoformat(slot["start"])
        if slot_dt.tzinfo is None:
            slot_dt = slot_dt.replace(tzinfo=UTC)

        # Slot IDs are opaque, but encode the instant in UTC so the booking
        # tool can parse them unambiguously.
        slot_dt_utc = slot_dt.astimezone(UTC)

        available_slots.append(TimeSlot(
            slot_id=f"slot_{property_id}_{slot_dt_utc.strftime('%Y%m%d_%H%M')}",
            datetime=slot_dt,
            available=True
        ))
        if len(available_slots) >= 10:
            break

    return GetAvailableSlotsOutput(
        property_id=property_id,
        slots=available_slots
    )


# ============================================================================
# TOOL METADATA
# ============================================================================

def get_tool_name() -> str:
    """Get tool name for registry."""
    return "get_available_slots"


def get_tool_definition() -> dict:
    """Get tool definition for LLM."""
    return TOOL_DEFINITION
