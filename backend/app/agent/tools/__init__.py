"""
Agent tools package.
All 9 tools that the AI agent can call during conversation.
"""

from app.agent.tools.availability import check_property_availability_tool
from app.agent.tools.booking import book_viewing_tool
from app.agent.tools.details import get_property_details_tool
from app.agent.tools.history import get_customer_history_tool
from app.agent.tools.leads import create_lead_tool, update_lead_tool
from app.agent.tools.notify import notify_sales_team_tool
from app.agent.tools.search import search_properties_tool
from app.agent.tools.slots import get_available_slots_tool

__all__ = [
    "search_properties_tool",
    "get_property_details_tool",
    "check_property_availability_tool",
    "create_lead_tool",
    "update_lead_tool",
    "get_available_slots_tool",
    "book_viewing_tool",
    "get_customer_history_tool",
    "notify_sales_team_tool",
]
