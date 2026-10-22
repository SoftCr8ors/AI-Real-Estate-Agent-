"""
Lead service - create and manage customer leads.
Handles lead creation, updates, and property interest tracking.
"""

import json

from sqlalchemy.orm import Session

from app.models.lead import Lead, LeadProperty, LeadSource, LeadStatus
from app.services.lead_status import auto_progress_lead, update_lead_status

# ============================================================================
# LEAD CREATION
# ============================================================================

def create_lead(
    db: Session,
    conversation_id: int,
    customer_id: int | None = None,
    requirements: str | None = None,
    notes: str | None = None,
    source: LeadSource = LeadSource.CHAT,
) -> Lead:
    """
    Create a new lead from conversation.

    Args:
        db: Database session
        conversation_id: Conversation ID that generated the lead
        customer_id: Customer ID (None for anonymous)
        requirements: JSON string of customer requirements
        notes: Additional notes
        source: Lead source (chat, form, phone, etc.)

    Returns:
        Created Lead object
    """
    # Check if lead already exists for this conversation
    existing = db.query(Lead).filter(
        Lead.conversation_id == conversation_id
    ).first()

    if existing:
        return existing

    # Create new lead
    lead = Lead(
        conversation_id=conversation_id,
        customer_id=customer_id,
        source=source,
        status=LeadStatus.NEW,
        requirements=requirements,
        notes=notes,
    )

    db.add(lead)
    db.commit()
    db.refresh(lead)

    return lead


def get_or_create_lead(
    db: Session,
    conversation_id: int,
    customer_id: int | None = None,
) -> tuple[Lead, bool]:
    """
    Get existing lead or create new one.

    Args:
        db: Database session
        conversation_id: Conversation ID
        customer_id: Customer ID (optional)

    Returns:
        Tuple of (Lead object, created: bool)
    """
    # Try to find existing lead
    lead = db.query(Lead).filter(
        Lead.conversation_id == conversation_id
    ).first()

    if lead:
        return lead, False

    # Create new lead
    lead = create_lead(
        db=db,
        conversation_id=conversation_id,
        customer_id=customer_id,
    )

    return lead, True


# ============================================================================
# LEAD UPDATES
# ============================================================================

def update_lead(
    db: Session,
    lead_id: int,
    requirements: str | None = None,
    notes: str | None = None,
    expected_timeline: str | None = None,
    assigned_to: int | None = None,
) -> Lead | None:
    """
    Update lead information.

    Args:
        db: Database session
        lead_id: Lead ID to update
        requirements: Updated requirements JSON string
        notes: Updated notes
        expected_timeline: Expected timeline
        assigned_to: Assign to admin user ID

    Returns:
        Updated Lead object or None if not found
    """
    lead = db.query(Lead).filter(Lead.id == lead_id).first()

    if not lead:
        return None

    # Update fields if provided
    if requirements is not None:
        lead.requirements = requirements

    if notes is not None:
        lead.notes = notes

    if expected_timeline is not None:
        lead.expected_timeline = expected_timeline

    if assigned_to is not None:
        lead.assigned_to = assigned_to

    db.commit()
    db.refresh(lead)

    return lead


def update_lead_requirements(
    db: Session,
    lead_id: int,
    customer_state: dict,
) -> Lead | None:
    """
    Update lead requirements from customer state.

    Args:
        db: Database session
        lead_id: Lead ID
        customer_state: Current customer state dict

    Returns:
        Updated Lead object or None if not found
    """
    lead = db.query(Lead).filter(Lead.id == lead_id).first()

    if not lead:
        return None

    # Extract requirements from customer state
    requirements = {
        "listing_type": customer_state.get("listing_type"),
        "location": customer_state.get("location"),
        "budget": customer_state.get("budget"),
        "bedrooms": customer_state.get("bedrooms"),
        "property_type": customer_state.get("property_type"),
        "timeline": customer_state.get("timeline"),
    }

    # Remove None values
    requirements = {k: v for k, v in requirements.items() if v is not None}

    # Store as JSON string
    lead.requirements = json.dumps(requirements)

    # Update timeline if available
    if customer_state.get("timeline"):
        lead.expected_timeline = customer_state["timeline"]

    db.commit()
    db.refresh(lead)

    # Auto-progress status if criteria met
    auto_progress_lead(db, lead_id, customer_state)

    return lead


# ============================================================================
# PROPERTY INTEREST TRACKING
# ============================================================================

def track_property_view(
    db: Session,
    lead_id: int,
    property_id: int,
) -> LeadProperty:
    """
    Track that customer viewed a property.

    Args:
        db: Database session
        lead_id: Lead ID
        property_id: Property ID viewed

    Returns:
        LeadProperty association record
    """
    # Check if already viewed
    existing = db.query(LeadProperty).filter(
        LeadProperty.lead_id == lead_id,
        LeadProperty.property_id == property_id,
    ).first()

    if existing:
        return existing

    # Create new view record
    lead_property = LeadProperty(
        lead_id=lead_id,
        property_id=property_id,
        interested=0,  # Just viewed, not interested yet
    )

    db.add(lead_property)
    db.commit()
    db.refresh(lead_property)

    return lead_property


def mark_property_interest(
    db: Session,
    lead_id: int,
    property_id: int,
    interested: bool = True,
) -> LeadProperty | None:
    """
    Mark customer interest in a property.

    Args:
        db: Database session
        lead_id: Lead ID
        property_id: Property ID
        interested: True if interested, False to remove interest

    Returns:
        Updated LeadProperty or None if not found
    """
    lead_property = db.query(LeadProperty).filter(
        LeadProperty.lead_id == lead_id,
        LeadProperty.property_id == property_id,
    ).first()

    if not lead_property:
        # Create if doesn't exist
        lead_property = track_property_view(db, lead_id, property_id)

    # Update interest
    lead_property.interested = 1 if interested else 0

    db.commit()
    db.refresh(lead_property)

    return lead_property


def get_lead_interested_properties(
    db: Session,
    lead_id: int,
) -> list[int]:
    """
    Get list of property IDs the customer is interested in.

    Args:
        db: Database session
        lead_id: Lead ID

    Returns:
        List of property IDs
    """
    lead_properties = db.query(LeadProperty).filter(
        LeadProperty.lead_id == lead_id,
        LeadProperty.interested == 1,
    ).all()

    return [lp.property_id for lp in lead_properties]


def get_lead_viewed_properties(
    db: Session,
    lead_id: int,
) -> list[int]:
    """
    Get list of all property IDs the customer has viewed.

    Args:
        db: Database session
        lead_id: Lead ID

    Returns:
        List of property IDs
    """
    lead_properties = db.query(LeadProperty).filter(
        LeadProperty.lead_id == lead_id,
    ).all()

    return [lp.property_id for lp in lead_properties]


# ============================================================================
# LEAD RETRIEVAL
# ============================================================================

def get_lead_by_id(db: Session, lead_id: int) -> Lead | None:
    """
    Get lead by ID.

    Args:
        db: Database session
        lead_id: Lead ID

    Returns:
        Lead object or None if not found
    """
    return db.query(Lead).filter(Lead.id == lead_id).first()


def get_lead_by_conversation(
    db: Session,
    conversation_id: int,
) -> Lead | None:
    """
    Get lead by conversation ID.

    Args:
        db: Database session
        conversation_id: Conversation ID

    Returns:
        Lead object or None if not found
    """
    return db.query(Lead).filter(
        Lead.conversation_id == conversation_id
    ).first()


def get_leads_by_customer(
    db: Session,
    customer_id: int,
    limit: int = 50,
) -> list[Lead]:
    """
    Get all leads for a customer.

    Args:
        db: Database session
        customer_id: Customer ID
        limit: Max results

    Returns:
        List of Lead objects
    """
    return db.query(Lead).filter(
        Lead.customer_id == customer_id
    ).order_by(Lead.created_at.desc()).limit(limit).all()


# ============================================================================
# LEAD STATUS MANAGEMENT
# ============================================================================

def mark_lead_lost(
    db: Session,
    lead_id: int,
    reason: str,
    changed_by: int | None = None,
) -> bool:
    """
    Mark lead as lost.

    Args:
        db: Database session
        lead_id: Lead ID
        reason: Reason for marking as lost
        changed_by: Admin user ID

    Returns:
        True if updated successfully
    """
    return update_lead_status(
        db=db,
        lead_id=lead_id,
        new_status=LeadStatus.LOST,
        reason=reason,
        changed_by=changed_by,
        automated=False,
    )


def mark_lead_converted(
    db: Session,
    lead_id: int,
    reason: str,
    changed_by: int | None = None,
) -> bool:
    """
    Mark lead as converted (deal closed).

    Args:
        db: Database session
        lead_id: Lead ID
        reason: Reason/details of conversion
        changed_by: Admin user ID

    Returns:
        True if updated successfully
    """
    return update_lead_status(
        db=db,
        lead_id=lead_id,
        new_status=LeadStatus.CONVERTED,
        reason=reason,
        changed_by=changed_by,
        automated=False,
    )
