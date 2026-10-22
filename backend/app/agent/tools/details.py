"""
Get property details tool.
AI agent uses this to fetch full property information.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.schemas.tools import GetPropertyDetailsInput, GetPropertyDetailsOutput, PropertyDetails
from app.services.search import get_property_details

# ============================================================================
# TOOL DEFINITION
# ============================================================================

TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "get_property_details",
        "description": (
            "Get complete details for a specific property by ID. "
            "Use this when customer asks for more information about a specific property, "
            "or wants to see full details, amenities, or images."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "property_id": {
                    "type": "integer",
                    "description": "The property ID to fetch details for",
                },
            },
            "required": ["property_id"],
        },
    },
}


# ============================================================================
# TOOL EXECUTION
# ============================================================================

def get_property_details_tool(
    db: Session,
    params: dict[str, Any],
) -> GetPropertyDetailsOutput:
    """
    Execute property details retrieval.

    Args:
        db: Database session
        params: Parameters from AI (property_id)

    Returns:
        GetPropertyDetailsOutput with full property info

    Raises:
        ValueError: If property not found
    """
    # Validate input
    input_data = GetPropertyDetailsInput(**params)

    # Get property from service
    property_obj = get_property_details(db, input_data.property_id)

    if not property_obj:
        raise ValueError(f"Property ID {input_data.property_id} not found")

    # Extract amenities
    amenities = [amenity.name for amenity in property_obj.amenities]

    # Extract images
    images = []
    if property_obj.images:
        sorted_images = sorted(property_obj.images, key=lambda x: x.display_order or 999)
        images = [img.image_url for img in sorted_images]

    # Get agent info (if available)
    agent_name = None
    agent_phone = None
    if hasattr(property_obj, 'agent') and property_obj.agent:
        agent_name = property_obj.agent.name
        agent_phone = property_obj.agent.phone

    # Build property details
    details = PropertyDetails(
        property_id=property_obj.id,
        title=property_obj.title,
        description=property_obj.description or "",
        location=property_obj.location,
        price=float(property_obj.price),
        bedrooms=property_obj.bedrooms,
        bathrooms=property_obj.bathrooms,
        area_sqft=property_obj.size_sqft,
        listing_type=property_obj.listing_type,
        property_type=property_obj.property_type,
        availability=property_obj.availability,
        amenities=amenities,
        images=images,
        agent_name=agent_name,
        agent_phone=agent_phone,
    )

    return GetPropertyDetailsOutput(
        property=details,
        availability_status=property_obj.availability,
    )


# ============================================================================
# TOOL METADATA
# ============================================================================

def get_tool_name() -> str:
    """Get tool name for registry."""
    return "get_property_details"


def get_tool_definition() -> dict:
    """Get tool definition for LLM."""
    return TOOL_DEFINITION
