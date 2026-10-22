"""
Lead management tools.
AI agent uses these to create and update customer leads.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.models.lead import LeadStatus
from app.schemas.tools import (
    CreateLeadInput,
    CreateLeadOutput,
    UpdateLeadInput,
    UpdateLeadOutput,
)
from app.services.lead_status import update_lead_status
from app.services.leads import get_or_create_lead, update_lead

# ============================================================================
# CREATE LEAD TOOL
# ============================================================================

CREATE_LEAD_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "create_lead",
        "description": (
            "Create a lead when customer shows serious interest. "
            "Use this when customer: asks to schedule viewing, requests contact, "
            "provides contact info, or shows strong purchase/rental intent."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "conversation_id": {
                    "type": "integer",
                    "description": "Current conversation ID",
                },
                "customer_id": {
                    "type": "integer",
                    "description": "Customer ID if known (optional)",
                },
                "requirements": {
                    "type": "string",
                    "description": "JSON string of customer requirements (listing_type, location, budget, etc.)",
                },
                "notes": {
                    "type": "string",
                    "description": "Additional notes about the lead",
                },
            },
            "required": ["conversation_id"],
        },
    },
}


def create_lead_tool(
    db: Session,
    params: dict[str, Any],
) -> CreateLeadOutput:
    """
    Execute lead creation.

    Args:
        db: Database session
        params: Parameters from AI

    Returns:
        CreateLeadOutput with lead ID and status
    """
    # Validate input
    input_data = CreateLeadInput(**params)

    # Get or create lead (idempotent)
    lead, created = get_or_create_lead(
        db=db,
        conversation_id=input_data.conversation_id,
        customer_id=input_data.customer_id,
    )

    # Update lead info if provided
    if input_data.requirements or input_data.notes:
        update_lead(
            db=db,
            lead_id=lead.id,
            requirements=input_data.requirements,
            notes=input_data.notes,
        )

    return CreateLeadOutput(
        lead_id=lead.id,
        status=lead.status.value,
        created=created,
    )


# ============================================================================
# UPDATE LEAD TOOL
# ============================================================================

UPDATE_LEAD_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "update_lead",
        "description": (
            "Update an existing lead with new information or status. "
            "Use this to update requirements, notes, timeline, or progress lead status."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "lead_id": {
                    "type": "integer",
                    "description": "Lead ID to update",
                },
                "status": {
                    "type": "string",
                    "enum": ["new", "warm", "hot", "qualified", "viewing_scheduled"],
                    "description": "New lead status (optional)",
                },
                "requirements": {
                    "type": "string",
                    "description": "Updated requirements JSON string (optional)",
                },
                "notes": {
                    "type": "string",
                    "description": "Updated notes (optional)",
                },
                "expected_timeline": {
                    "type": "string",
                    "description": "Expected timeline: within_1_month, 1-3_months, 3-6_months, 6+_months",
                },
            },
            "required": ["lead_id"],
        },
    },
}


def update_lead_tool(
    db: Session,
    params: dict[str, Any],
) -> UpdateLeadOutput:
    """
    Execute lead update.

    Args:
        db: Database session
        params: Parameters from AI

    Returns:
        UpdateLeadOutput with old and new status

    Raises:
        ValueError: If lead not found
    """
    # Validate input
    input_data = UpdateLeadInput(**params)

    # Get current lead
    from app.services.leads import get_lead_by_id
    lead = get_lead_by_id(db, input_data.lead_id)

    if not lead:
        raise ValueError(f"Lead ID {input_data.lead_id} not found")

    old_status = lead.status.value

    # Update status if provided
    if input_data.status:
        new_status = LeadStatus(input_data.status)
        update_lead_status(
            db=db,
            lead_id=input_data.lead_id,
            new_status=new_status,
            reason="Updated by AI agent based on conversation",
            automated=True,
        )

    # Update other fields
    updated_lead = update_lead(
        db=db,
        lead_id=input_data.lead_id,
        requirements=input_data.requirements,
        notes=input_data.notes,
        expected_timeline=input_data.expected_timeline,
    )

    if not updated_lead:
        raise ValueError(f"Failed to update lead {input_data.lead_id}")

    return UpdateLeadOutput(
        lead_id=updated_lead.id,
        old_status=old_status,
        new_status=updated_lead.status.value,
        updated=True,
    )


# ============================================================================
# TOOL METADATA
# ============================================================================

def get_create_lead_tool_name() -> str:
    """Get create_lead tool name."""
    return "create_lead"


def get_create_lead_tool_definition() -> dict:
    """Get create_lead tool definition."""
    return CREATE_LEAD_TOOL_DEFINITION


def get_update_lead_tool_name() -> str:
    """Get update_lead tool name."""
    return "update_lead"


def get_update_lead_tool_definition() -> dict:
    """Get update_lead tool definition."""
    return UPDATE_LEAD_TOOL_DEFINITION
