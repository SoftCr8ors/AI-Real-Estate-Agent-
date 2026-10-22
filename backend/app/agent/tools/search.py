"""
Search properties tool.
AI agent uses this to search the property database.
"""

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.schemas.tools import SearchPropertiesInput, SearchPropertiesOutput, PropertySummary
from app.services.search import search_properties


# ============================================================================
# TOOL DEFINITION
# ============================================================================

TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "search_properties",
        "description": (
            "Search for properties matching customer criteria. "
            "Returns a list of matching properties with relevance scores. "
            "Use this when customer asks to see properties or provides search criteria."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "listing_type": {
                    "type": "string",
                    "enum": ["buy", "rent"],
                    "description": "Type of listing: 'buy' for purchase, 'rent' for rental",
                },
                "location": {
                    "type": "string",
                    "description": "Location, area, or neighborhood (e.g., 'Dubai Marina', 'JVC')",
                },
                "min_price": {
                    "type": "number",
                    "description": "Minimum price in AED",
                },
                "max_price": {
                    "type": "number",
                    "description": "Maximum price/budget in AED",
                },
                "bedrooms": {
                    "type": "integer",
                    "description": "Number of bedrooms (0 for studio)",
                },
                "property_type": {
                    "type": "string",
                    "enum": ["apartment", "villa", "townhouse", "penthouse"],
                    "description": "Type of property",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default 10, max 50)",
                    "default": 10,
                },
            },
            "required": [],
        },
    },
}


# ============================================================================
# TOOL EXECUTION
# ============================================================================

def search_properties_tool(
    db: Session,
    params: dict[str, Any],
) -> SearchPropertiesOutput:
    """
    Execute property search.
    
    Args:
        db: Database session
        params: Search parameters from AI
        
    Returns:
        SearchPropertiesOutput with results
    """
    # Validate input
    input_data = SearchPropertiesInput(**params)
    
    # Convert to service parameters
    search_params = {
        "listing_type": input_data.listing_type,
        "location": input_data.location,
        "min_price": Decimal(str(input_data.min_price)) if input_data.min_price else None,
        "max_price": Decimal(str(input_data.max_price)) if input_data.max_price else None,
        "bedrooms": input_data.bedrooms,
        "property_type": input_data.property_type,
    }
    
    # Call search service
    results = search_properties(db, **search_params)
    
    # Build query summary
    query_parts = []
    if input_data.listing_type:
        query_parts.append(f"for {input_data.listing_type}")
    if input_data.bedrooms is not None:
        br = "studio" if input_data.bedrooms == 0 else f"{input_data.bedrooms} bedroom"
        query_parts.append(br)
    if input_data.location:
        query_parts.append(f"in {input_data.location}")
    if input_data.max_price:
        query_parts.append(f"under AED {input_data.max_price:,.0f}")
    
    query_summary = "Properties " + " ".join(query_parts) if query_parts else "All available properties"
    
    # Convert to output format
    property_summaries = []
    for result in results["properties"][:input_data.limit]:
        prop = result["property"]
        property_summaries.append(PropertySummary(
            property_id=prop.id,
            title=prop.title,
            location=prop.location,
            price=float(prop.price),
            bedrooms=prop.bedrooms,
            bathrooms=prop.bathrooms,
            area_sqft=prop.size_sqft,
            listing_type=prop.listing_type,
            property_type=prop.property_type,
            relevance_score=result["score"],
        ))
    
    return SearchPropertiesOutput(
        properties=property_summaries,
        total_found=results["total"],
        query_understood=query_summary,
    )


# ============================================================================
# TOOL METADATA
# ============================================================================

def get_tool_name() -> str:
    """Get tool name for registry."""
    return "search_properties"


def get_tool_definition() -> dict:
    """Get tool definition for LLM."""
    return TOOL_DEFINITION