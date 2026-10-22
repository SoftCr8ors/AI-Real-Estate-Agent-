
"""
Book viewing appointment tool.
AI agent uses this to book property viewings.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.lead import Lead
from app.schemas.tools import BookViewingOutput
from app.services.booking import BookingError, book_viewing

# ============================================================================
# TOOL DEFINITION
# ============================================================================

TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "book_viewing",
        "description": (
            "Book a property viewing appointment for the customer. "
            "Use this after customer selects a time slot and provides contact information."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "lead_id": {
                    "type": "integer",
                    "description": "Lead ID for this booking",
                },
                "property_id": {
                    "type": "integer",
                    "description": "Property ID to view",
                },
                "slot_id": {
                    "type": "string",
                    "description": "Time slot ID from get_available_slots",
                },
                "customer_name": {
                    "type": "string",
                    "description": "Customer's full name",
                },
                "customer_phone": {
                    "type": "string",
                    "description": "Customer's phone number (phone or email is required)",
                },
                "customer_email": {
                    "type": "string",
                    "description": "Customer's email address (phone or email is required)",
                },
            },
            "required": ["lead_id", "property_id", "slot_id", "customer_name"],
        },
    },
}


# ============================================================================
# TOOL EXECUTION
# ============================================================================

def book_viewing_tool(
    db: Session,
    params: dict[str, Any],
) -> BookViewingOutput:
    """
    Execute viewing booking.

    Args:
        db: Database session
        params: Parameters from AI

    Returns:
        BookViewingOutput with booking confirmation

    Raises:
        ValueError: If booking validation fails
    """
    # Extract parameters
    lead_id = params.get("lead_id")
    property_id = params.get("property_id")
    slot_id = params.get("slot_id")
    customer_name = (params.get("customer_name") or "").strip()
    customer_phone = (params.get("customer_phone") or "").strip() or None
    customer_email = (params.get("customer_email") or "").strip() or None

    if not lead_id:
        raise ValueError("lead_id is required")
    if not property_id:
        raise ValueError("property_id is required")
    if not slot_id:
        raise ValueError("slot_id is required")
    if not customer_name:
        raise ValueError("customer_name is required")
    if not customer_phone and not customer_email:
        raise ValueError("customer_phone or customer_email is required")

    # Extract datetime from slot_id (format: slot_PROPERTYID_YYYYMMDD_HHMM)
    try:
        parts = slot_id.split("_")
        slot_property_id = int(parts[1])
        date_str = parts[2]  # YYYYMMDD
        time_str = parts[3]  # HHMM
        slot_datetime = datetime.strptime(
            f"{date_str}_{time_str}", "%Y%m%d_%H%M"
        ).replace(tzinfo=UTC)
    except (IndexError, ValueError) as e:
        raise ValueError(f"Invalid slot_id format: {slot_id}. Expected format: slot_<property_id>_YYYYMMDD_HHMM") from e

    if slot_property_id != int(property_id):
        raise ValueError(
            f"slot_id {slot_id} does not belong to property {property_id}"
        )

    # The booking service needs a lead with a linked customer that has a name
    # and at least one contact channel. Persist what the customer just told us
    # before booking so a brand-new chat lead can complete a viewing.
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if lead is None:
        raise ValueError(f"Lead {lead_id} not found")

    _resolve_customer(
        db=db,
        lead=lead,
        name=customer_name,
        phone=customer_phone,
        email=customer_email,
    )

    # Optional notes from params
    notes = params.get("notes")

    # Book the viewing using booking service
    try:
        appointment = book_viewing(
            db=db,
            lead_id=lead.id,
            property_id=property_id,
            scheduled_at=slot_datetime,
            notes=notes
        )

        # Return success
        return BookViewingOutput(
            booking_id=appointment.id,
            confirmed=True,
            slot_datetime=appointment.scheduled_at,
            confirmation_sent=appointment.sync_status == "synced",  # True if Google Calendar synced
            message=(
                f"Your viewing has been confirmed for {appointment.scheduled_at.strftime('%B %d, %Y at %I:%M %p')}. "
                + (
                    "You'll receive a calendar invitation shortly."
                    if appointment.sync_status == "synced"
                    else "Our team will contact you with the details."
                )
            )
        )

    except BookingError as e:
        # Booking validation failed - return error for AI to communicate
        return BookViewingOutput(
            booking_id=0,
            confirmed=False,
            slot_datetime=slot_datetime,
            confirmation_sent=False,
            message=f"I apologize, but I couldn't complete the booking: {str(e)}. Would you like to try a different time slot?"
        )


def _resolve_customer(
    db: Session,
    lead: Lead,
    name: str,
    phone: str | None,
    email: str | None,
) -> Customer:
    """Attach the given contact details to the lead's customer record.

    Reuses the lead's existing customer when present, otherwise tries to match
    an existing customer by phone/email, otherwise creates a new one. Only
    fills blank fields so we never overwrite data captured earlier.
    """
    customer = lead.customer

    if customer is None:
        if phone:
            customer = db.query(Customer).filter(Customer.phone == phone).first()
        if customer is None and email:
            customer = db.query(Customer).filter(Customer.email == email).first()
        if customer is None:
            customer = Customer(name=name, phone=phone, email=email)
            db.add(customer)
            db.flush()

        lead.customer_id = customer.id

    if not customer.name:
        customer.name = name
    if not customer.phone and phone:
        customer.phone = phone
    if not customer.email and email:
        customer.email = email

    # Keep the conversation record in sync for the chat UI / customer state
    if lead.conversation_id:
        conversation = (
            db.query(Conversation)
            .filter(Conversation.id == lead.conversation_id)
            .first()
        )
        if conversation:
            if not conversation.customer_name:
                conversation.customer_name = customer.name
            if not conversation.customer_phone and customer.phone:
                conversation.customer_phone = customer.phone
            if not conversation.customer_email and customer.email:
                conversation.customer_email = customer.email

    db.commit()
    db.refresh(lead)
    return customer


# ============================================================================
# TOOL METADATA
# ============================================================================

def get_tool_name() -> str:
    """Get tool name for registry."""
    return "book_viewing"


def get_tool_definition() -> dict:
    """Get tool definition for LLM."""
    return TOOL_DEFINITION
