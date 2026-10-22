
"""
Book viewing appointment tool (STUB).
AI agent uses this to book property viewings.
"""

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.schemas.tools import BookViewingInput, BookViewingOutput


# ============================================================================
# TOOL DEFINITION
# ============================================================================

TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "book_viewing",
        "description": (
            "Book a property viewing appointment for the customer. "
            "Use this after customer selects a time slot and provides contact information."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "lead_id": {
                    "type": "integer",
                    "description": "Lead ID for this booking",
                },
                "property_id": {
                    "type": "integer",
                    "description": "Property ID to view",
                },
                "slot_id": {
                    "type": "string",
                    "description": "Time slot ID from get_available_slots",
                },
                "customer_name": {
                    "type": "string",
                    "description": "Customer's full name",
                },
                "customer_phone": {
                    "type": "string",
                    "description": "Customer's phone number",
                },
                "customer_email": {
                    "type": "string",
                    "description": "Customer's email address (optional)",
                },
            },
            "required": ["lead_id", "property_id", "slot_id", "customer_name", "customer_phone"],
        },
    },
}


# ============================================================================
# TOOL EXECUTION (STUB)
# ============================================================================

def book_viewing_tool(
    db: Session,
    params: dict[str, Any],
) -> BookViewingOutput:
    """
    Execute viewing booking (STUB - simulates booking).
    
    Args:
        db: Database session
        params: Parameters from AI
        
    Returns:
        BookViewingOutput with booking confirmation
    """
    # Validate input
    input_data = BookViewingInput(**params)
    
    # STUB: Simulate booking
    # In production, this would:
    # 1. Check slot availability
    # 2. Create booking in calendar system
    # 3. Send confirmation email/SMS
    # 4. Update lead status to VIEWING_SCHEDULED
    # 5. Notify assigned agent
    
    # Extract datetime from slot_id (format: slot_PROPERTYID_YYYYMMDD_HHMM)
    try:
        parts = input_data.slot_id.split("_")
        date_str = parts[2]  # YYYYMMDD
        time_str = parts[3]  # HHMM
        slot_datetime = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M")
    except (IndexError, ValueError):
        # Fallback to current time + 1 day
        slot_datetime = datetime.utcnow().replace(hour=10, minute=0, second=0, microsecond=0)
    
    # Generate mock booking ID
    booking_id = abs(hash(input_data.slot_id)) % 100000
    
    # Update lead status to VIEWING_SCHEDULED
    from app.models.lead import LeadStatus
    from app.services.lead_status import update_lead_status
    
    update_lead_status(
        db=db,
        lead_id=input_data.lead_id,
        new_status=LeadStatus.VIEWING_SCHEDULED,
        reason=f"Viewing booked for {slot_datetime.strftime('%Y-%m-%d %H:%M')}",
        automated=True,
    )
    
    return BookViewingOutput(
        booking_id=booking_id,
        confirmed=True,
        slot_datetime=slot_datetime,
        confirmation_sent=True,  # Stub: pretend we sent confirmation
    )


# ============================================================================
# TOOL METADATA
# ============================================================================

def get_tool_name() -> str:
    """Get tool name for registry."""
    return "book_viewing"


def get_tool_definition() -> dict:
    """Get tool definition for LLM."""
    return TOOL_DEFINITION
