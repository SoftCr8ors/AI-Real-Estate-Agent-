"""
Get available viewing slots tool (STUB).
AI agent uses this to check available appointment times.
"""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.schemas.tools import GetAvailableSlotsInput, GetAvailableSlotsOutput, TimeSlot


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
# TOOL EXECUTION (STUB)
# ============================================================================

def get_available_slots_tool(
    db: Session,
    params: dict[str, Any],
) -> GetAvailableSlotsOutput:
    """
    Execute viewing slots retrieval (STUB - returns mock data).
    
    Args:
        db: Database session
        params: Parameters from AI (property_id, date_from, date_to)
        
    Returns:
        GetAvailableSlotsOutput with available time slots
    """
    # Validate input
    input_data = GetAvailableSlotsInput(**params)
    
    # STUB: Generate mock available slots
    # In production, this would query a calendar/booking system
    
    slots = []
    current_date = datetime.strptime(input_data.date_from, "%Y-%m-%d")
    end_date = datetime.strptime(input_data.date_to, "%Y-%m-%d")
    
    # Generate morning (10 AM) and afternoon (2 PM) slots for next 7 days
    while current_date <= end_date and len(slots) < 14:
        # Skip weekends for this stub
        if current_date.weekday() < 5:  # Monday = 0, Friday = 4
            # Morning slot
            morning = current_date.replace(hour=10, minute=0, second=0)
            slots.append(TimeSlot(
                slot_id=f"slot_{input_data.property_id}_{morning.strftime('%Y%m%d_%H%M')}",
                datetime=morning,
                available=True,
            ))
            
            # Afternoon slot
            afternoon = current_date.replace(hour=14, minute=0, second=0)
            slots.append(TimeSlot(
                slot_id=f"slot_{input_data.property_id}_{afternoon.strftime('%Y%m%d_%H%M')}",
                datetime=afternoon,
                available=True,
            ))
        
        current_date += timedelta(days=1)
    
    return GetAvailableSlotsOutput(
        property_id=input_data.property_id,
        slots=slots[:10],  # Return max 10 slots
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