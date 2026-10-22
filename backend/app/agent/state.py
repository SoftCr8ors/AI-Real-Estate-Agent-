"""
Conversation state management.
Tracks customer information and conversation context.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.services.conversation import (
    get_conversation_state,
    update_conversation_state,
    update_customer_info,
)

# ============================================================================
# CONVERSATION STATE
# ============================================================================

class ConversationState:
    """
    Manages conversation state and customer information.
    State is persisted to database after each update.
    """

    def __init__(self, db: Session, conversation_id: int):
        """
        Initialize conversation state.

        Args:
            db: Database session
            conversation_id: Conversation ID
        """
        self.db = db
        self.conversation_id = conversation_id
        self._state = get_conversation_state(db, conversation_id) or {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get a state value."""
        return self._state.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a state value."""
        self._state[key] = value

    def update(self, updates: dict) -> None:
        """Update multiple state values."""
        self._state.update(updates)

    def delete(self, key: str) -> None:
        """Remove a state value."""
        self._state.pop(key, None)

    def get_all(self) -> dict:
        """Get entire state dict."""
        return self._state.copy()

    def save(self) -> None:
        """Persist state to database."""
        from app.agent.prompts import build_state_summary

        # Build state summary
        summary = build_state_summary(self._state)

        # Save to database
        update_conversation_state(
            db=self.db,
            conversation_id=self.conversation_id,
            customer_state=self._state,
            state_summary=summary,
        )

    # ========================================================================
    # CUSTOMER INFO HELPERS
    # ========================================================================

    def set_listing_type(self, listing_type: str) -> None:
        """Set listing type (buy/rent)."""
        old_type = self._state.get("listing_type")

        # If switching between buy/rent, clear budget
        if old_type and old_type != listing_type:
            self._state.pop("budget", None)

        self._state["listing_type"] = listing_type

    def set_location(self, location: str) -> None:
        """Set preferred location."""
        self._state["location"] = location

    def set_budget(self, budget: float) -> None:
        """Set budget in AED."""
        self._state["budget"] = budget

    def set_bedrooms(self, bedrooms: int) -> None:
        """Set number of bedrooms (0 for studio)."""
        self._state["bedrooms"] = bedrooms

    def set_property_type(self, property_type: str) -> None:
        """Set property type."""
        self._state["property_type"] = property_type

    def set_contact_info(self, name: str | None = None, email: str | None = None, phone: str | None =
None) -> None:
        """Set customer contact information."""
        if name:
            self._state["name"] = name
        if email:
            self._state["email"] = email
        if phone:
            self._state["phone"] = phone

        # Also update conversation table
        update_customer_info(
            db=self.db,
            conversation_id=self.conversation_id,
            name=name,
            email=email,
            phone=phone,
        )

    def set_timeline(self, timeline: str) -> None:
        """Set expected timeline."""
        self._state["timeline"] = timeline

    def increment_properties_viewed(self) -> None:
        """Increment properties viewed counter."""
        count = self._state.get("properties_viewed", 0)
        self._state["properties_viewed"] = count + 1

    def set_last_search(self, query: str) -> None:
        """Set last search query."""
        self._state["last_search_query"] = query

    def set_selected_property(self, property_id: int) -> None:
        """Set selected/interested property."""
        self._state["selected_property_id"] = property_id

    def set_requested_viewing(self, requested: bool = True) -> None:
        """Mark that customer requested a viewing."""
        self._state["requested_viewing"] = requested

    def set_requested_handoff(self, requested: bool = True) -> None:
        """Mark that customer requested handoff to human."""
        self._state["requested_handoff"] = requested

    def set_appointment_booked(self, booked: bool = True) -> None:
        """Mark that appointment was booked."""
        self._state["appointment_booked"] = booked

    # ========================================================================
    # STATE QUERIES
    # ========================================================================

    def has_basic_info(self) -> bool:
        """Check if we have basic search criteria."""
        return bool(
            self._state.get("listing_type") and
            (self._state.get("location") or self._state.get("budget"))
        )

    def has_contact_info(self) -> bool:
        """Check if we have customer contact info."""
        return bool(
            self._state.get("name") and
            (self._state.get("phone") or self._state.get("email"))
        )

    def is_qualified_lead(self) -> bool:
        """Check if customer is a qualified lead."""
        return bool(
            self._state.get("name") and
            (self._state.get("phone") or self._state.get("email")) and
            self._state.get("listing_type") and
            self._state.get("budget") and
            self._state.get("location")
        )

    def get_search_criteria(self) -> dict:
        """Get search criteria from state."""
        return {
            "listing_type": self._state.get("listing_type"),
            "location": self._state.get("location"),
            "min_price": None,
            "max_price": self._state.get("budget"),
            "bedrooms": self._state.get("bedrooms"),
            "property_type": self._state.get("property_type"),
        }


# ============================================================================
# STATE FACTORY
# ============================================================================

def load_conversation_state(db: Session, conversation_id: int) -> ConversationState:
    """
    Load conversation state from database.

    Args:
        db: Database session
        conversation_id: Conversation ID

    Returns:
        ConversationState instance
    """
    return ConversationState(db, conversation_id)
