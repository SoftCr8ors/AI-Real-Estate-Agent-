"""
Get customer history tool.
AI agent uses this to retrieve customer's past interactions and interests.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.schemas.tools import (
    CustomerInteraction,
    GetCustomerHistoryInput,
    GetCustomerHistoryOutput,
)
from app.services.leads import get_lead_by_conversation, get_lead_viewed_properties

# ============================================================================
# TOOL DEFINITION
# ============================================================================

TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "get_customer_history",
        "description": (
            "Get customer's interaction history including past conversations, "
            "viewed properties, and current lead status. "
            "Use this to personalize responses or avoid repeating information."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "integer",
                    "description": "Customer ID (optional)",
                },
                "conversation_id": {
                    "type": "integer",
                    "description": "Current conversation ID (optional)",
                },
            },
            "required": [],
        },
    },
}


# ============================================================================
# TOOL EXECUTION
# ============================================================================

def get_customer_history_tool(
    db: Session,
    params: dict[str, Any],
) -> GetCustomerHistoryOutput:
    """
    Execute customer history retrieval.

    Args:
        db: Database session
        params: Parameters from AI (customer_id or conversation_id)

    Returns:
        GetCustomerHistoryOutput with interaction history
    """
    # Validate input
    input_data = GetCustomerHistoryInput(**params)

    customer_id = input_data.customer_id
    conversation_id = input_data.conversation_id

    # Get lead if conversation_id provided
    lead = None
    if conversation_id:
        lead = get_lead_by_conversation(db, conversation_id)
        if lead and not customer_id:
            customer_id = lead.customer_id

    # Build interactions list
    interactions = []
    total_conversations = 0
    total_properties_viewed = 0
    current_lead_status = None

    if lead:
        current_lead_status = lead.status.value

        # Get viewed properties
        viewed_property_ids = get_lead_viewed_properties(db, lead.id)
        total_properties_viewed = len(viewed_property_ids)

        # Create interaction records for viewed properties
        from app.services.search import get_property_details
        for prop_id in viewed_property_ids[:10]:  # Limit to last 10
            prop = get_property_details(db, prop_id)
            if prop:
                interactions.append(CustomerInteraction(
                    date=lead.created_at,
                    type="viewed",
                    property_id=prop.id,
                    property_title=prop.title,
                    notes=None,
                ))

    # Get customer's other conversations if customer_id available
    if customer_id:
        from app.models.conversation import Conversation
        conversations = db.query(Conversation).filter(
            Conversation.customer_id == customer_id
        ).all()
        total_conversations = len(conversations)

        # Get all leads for customer
        from app.services.leads import get_leads_by_customer
        customer_leads = get_leads_by_customer(db, customer_id, limit=10)

        for customer_lead in customer_leads:
            if customer_lead.id != (lead.id if lead else None):
                interactions.append(CustomerInteraction(
                    date=customer_lead.created_at,
                    type="contacted",
                    property_id=None,
                    property_title=None,
                    notes=f"Previous lead: {customer_lead.status.value}",
                ))

    # Sort interactions by date (most recent first)
    interactions.sort(key=lambda x: x.date, reverse=True)

    return GetCustomerHistoryOutput(
        customer_id=customer_id,
        total_conversations=total_conversations,
        total_properties_viewed=total_properties_viewed,
        interactions=interactions[:20],  # Return max 20 interactions
        current_lead_status=current_lead_status,
    )


# ============================================================================
# TOOL METADATA
# ============================================================================

def get_tool_name() -> str:
    """Get tool name for registry."""
    return "get_customer_history"


def get_tool_definition() -> dict:
    """Get tool definition for LLM."""
    return TOOL_DEFINITION
