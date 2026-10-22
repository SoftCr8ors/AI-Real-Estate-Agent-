"""
Notify sales team tool (STUB).
AI agent uses this to alert human agents about hot leads.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.schemas.tools import NotifySalesTeamInput, NotifySalesTeamOutput

# ============================================================================
# TOOL DEFINITION
# ============================================================================

TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "notify_sales_team",
        "description": (
            "Send notification to sales team about a lead that needs attention. "
            "Use this when customer requests immediate contact, has urgent timeline, "
            "or when lead reaches HOT/QUALIFIED status and needs human follow-up."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "lead_id": {
                    "type": "integer",
                    "description": "Lead ID to notify about",
                },
                "urgency": {
                    "type": "string",
                    "enum": ["low", "normal", "high", "urgent"],
                    "description": "Urgency level of the notification",
                    "default": "normal",
                },
                "message": {
                    "type": "string",
                    "description": "Additional message or context for sales team",
                },
            },
            "required": ["lead_id"],
        },
    },
}


# ============================================================================
# TOOL EXECUTION (STUB)
# ============================================================================

def notify_sales_team_tool(
    db: Session,
    params: dict[str, Any],
) -> NotifySalesTeamOutput:
    """
    Execute sales team notification (STUB - simulates notification).

    Args:
        db: Database session
        params: Parameters from AI

    Returns:
        NotifySalesTeamOutput with notification confirmation
    """
    # Validate input
    input_data = NotifySalesTeamInput(**params)

    # STUB: Simulate notification
    # In production, this would:
    # 1. Get lead details
    # 2. Find available agents (or assigned agent)
    # 3. Send notification via:
    #    - Email
    #    - SMS
    #    - Internal dashboard alert
    #    - Slack/Teams webhook
    # 4. Log notification in database

    # Get lead to check assigned agent
    from app.services.leads import get_lead_by_id
    lead = get_lead_by_id(db, input_data.lead_id)

    if not lead:
        raise ValueError(f"Lead ID {input_data.lead_id} not found")

    # Mock: Determine who to notify
    notified_agents = []

    if lead.assigned_to:
        # Notify assigned agent
        notified_agents.append(f"Agent_{lead.assigned_to}")
    else:
        # Notify team lead based on urgency
        if input_data.urgency in ["high", "urgent"]:
            notified_agents.append("TeamLead_Sales")
        else:
            notified_agents.append("Sales_Queue")

    # Generate mock notification ID
    import hashlib
    notification_id = hashlib.md5(
        f"{input_data.lead_id}_{input_data.urgency}".encode()
    ).hexdigest()[:12]

    return NotifySalesTeamOutput(
        notification_sent=True,
        notified_agents=notified_agents,
        notification_id=notification_id,
    )


# ============================================================================
# TOOL METADATA
# ============================================================================

def get_tool_name() -> str:
    """Get tool name for registry."""
    return "notify_sales_team"


def get_tool_definition() -> dict:
    """Get tool definition for LLM."""
    return TOOL_DEFINITION
