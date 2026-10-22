"""
Check property availability tool.
AI agent uses this to verify if a property is still available.
"""

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.schemas.tools import CheckAvailabilityInput, CheckAvailabilityOutput
from app.services.search import check_property_availability

# ============================================================================
# TOOL DEFINITION
# ============================================================================

TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "check_property_availability",
        "description": (
            "Check if a specific property is currently available. "
            "Use this when customer asks if a property is still available, "
            "or before booking a viewing to confirm availability status."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "property_id": {
                    "type": "integer",
                    "description": "The property ID to check availability for",
                },
            },
            "required": ["property_id"],
        },
    },
}


# ============================================================================
# TOOL EXECUTION
# ============================================================================

def check_property_availability_tool(
    db: Session,
    params: dict[str, Any],
) -> CheckAvailabilityOutput:
    """
    Execute property availability check.

    Args:
        db: Database session
        params: Parameters from AI (property_id)

    Returns:
        CheckAvailabilityOutput with availability status

    Raises:
        ValueError: If property not found
    """
    # Validate input
    input_data = CheckAvailabilityInput(**params)

    # Check availability from service
    availability_status = check_property_availability(db, input_data.property_id)

    if availability_status is None:
        raise ValueError(f"Property ID {input_data.property_id} not found")

    # Determine if available
    available = availability_status == "available"

    return CheckAvailabilityOutput(
        property_id=input_data.property_id,
        available=available,
        status=availability_status,
        last_updated=datetime.utcnow(),
    )


# ============================================================================
# TOOL METADATA
# ============================================================================

def get_tool_name() -> str:
    """Get tool name for registry."""
    return "check_property_availability"


def get_tool_definition() -> dict:
    """Get tool definition for LLM."""
    return TOOL_DEFINITION
