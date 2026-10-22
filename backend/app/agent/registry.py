"""
Tool registry.
Registers all tools and provides them to the LLM client.
"""

from typing import Any, Callable

from sqlalchemy.orm import Session

from app.agent.tools.availability import (
    check_property_availability_tool,
    get_tool_definition as get_availability_definition,
    get_tool_name as get_availability_name,
)
from app.agent.tools.booking import (
    book_viewing_tool,
    get_tool_definition as get_booking_definition,
    get_tool_name as get_booking_name,
)
from app.agent.tools.details import (
    get_property_details_tool,
    get_tool_definition as get_details_definition,
    get_tool_name as get_details_name,
)
from app.agent.tools.history import (
    get_customer_history_tool,
    get_tool_definition as get_history_definition,
    get_tool_name as get_history_name,
)
from app.agent.tools.leads import (
    create_lead_tool,
    get_create_lead_tool_definition,
    get_create_lead_tool_name,
    get_update_lead_tool_definition,
    get_update_lead_tool_name,
    update_lead_tool,
)
from app.agent.tools.notify import (
    get_tool_definition as get_notify_definition,
    get_tool_name as get_notify_name,
    notify_sales_team_tool,
)
from app.agent.tools.search import (
    get_tool_definition as get_search_definition,
    get_tool_name as get_search_name,
    search_properties_tool,
)
from app.agent.tools.slots import (
    get_available_slots_tool,
    get_tool_definition as get_slots_definition,
    get_tool_name as get_slots_name,
)


# ============================================================================
# TOOL REGISTRY
# ============================================================================

class ToolRegistry:
    """Registry of all available tools for the AI agent."""
    
    def __init__(self):
        self._tools: dict[str, Callable] = {}
        self._definitions: dict[str, dict] = {}
    
    def register(self, name: str, func: Callable, definition: dict) -> None:
        """
        Register a tool.
        
        Args:
            name: Tool name
            func: Tool execution function
            definition: Tool definition for LLM
        """
        self._tools[name] = func
        self._definitions[name] = definition
    
    def get_tool(self, name: str) -> Callable:
        """Get tool execution function by name."""
        if name not in self._tools:
            raise ValueError(f"Tool '{name}' not found in registry")
        return self._tools[name]
    
    def get_all_definitions(self) -> list[dict]:
        """Get all tool definitions for LLM."""
        return list(self._definitions.values())
    
    def get_tool_names(self) -> list[str]:
        """Get list of all registered tool names."""
        return list(self._tools.keys())
    
    def execute_tool(self, db: Session, name: str, params: dict[str, Any]) -> Any:
        """
        Execute a tool by name.
        
        Args:
            db: Database session
            name: Tool name
            params: Tool parameters
            
        Returns:
            Tool execution result
        """
        tool_func = self.get_tool(name)
        return tool_func(db, params)


# ============================================================================
# GLOBAL REGISTRY
# ============================================================================

_registry = ToolRegistry()


def register_all_tools() -> None:
    """Register all tools in the global registry."""
    
    # 1. Search properties
    _registry.register(
        name=get_search_name(),
        func=search_properties_tool,
        definition=get_search_definition(),
    )
    
    # 2. Get property details
    _registry.register(
        name=get_details_name(),
        func=get_property_details_tool,
        definition=get_details_definition(),
    )
    
    # 3. Check availability
    _registry.register(
        name=get_availability_name(),
        func=check_property_availability_tool,
        definition=get_availability_definition(),
    )
    
    # 4. Create lead
    _registry.register(
        name=get_create_lead_tool_name(),
        func=create_lead_tool,
        definition=get_create_lead_tool_definition(),
    )
    
    # 5. Update lead
    _registry.register(
        name=get_update_lead_tool_name(),
        func=update_lead_tool,
        definition=get_update_lead_tool_definition(),
    )
    
    # 6. Get available slots (stub)
    _registry.register(
        name=get_slots_name(),
        func=get_available_slots_tool,
        definition=get_slots_definition(),
    )
    
    # 7. Book viewing (stub)
    _registry.register(
        name=get_booking_name(),
        func=book_viewing_tool,
        definition=get_booking_definition(),
    )
    
    # 8. Get customer history
    _registry.register(
        name=get_history_name(),
        func=get_customer_history_tool,
        definition=get_history_definition(),
    )
    
    # 9. Notify sales team (stub)
    _registry.register(
        name=get_notify_name(),
        func=notify_sales_team_tool,
        definition=get_notify_definition(),
    )


def get_registry() -> ToolRegistry:
    """Get the global tool registry."""
    return _registry


def get_all_tools() -> list[dict]:
    """Get all tool definitions for LLM."""
    return _registry.get_all_definitions()


def execute_tool(db: Session, tool_name: str, params: dict[str, Any]) -> Any:
    """
    Execute a tool by name.
    
    Args:
        db: Database session
        tool_name: Tool name
        params: Tool parameters
        
    Returns:
        Tool execution result
    """
    return _registry.execute_tool(db, tool_name, params)


# Auto-register all tools on import
register_all_tools()