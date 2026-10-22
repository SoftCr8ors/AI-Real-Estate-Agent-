"""
Lead status management service.
Handles automated lead status progression with business rules.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.lead import Lead, LeadStatus, LeadStatusHistory


# ============================================================================
# STATUS PROGRESSION RULES
# ============================================================================

# Valid status transitions (only forward progression)
VALID_TRANSITIONS = {
    LeadStatus.NEW: [LeadStatus.WARM, LeadStatus.HOT, LeadStatus.QUALIFIED, LeadStatus.LOST],
    LeadStatus.WARM: [LeadStatus.HOT, LeadStatus.QUALIFIED, LeadStatus.LOST],
    LeadStatus.HOT: [LeadStatus.QUALIFIED, LeadStatus.VIEWING_SCHEDULED, LeadStatus.LOST],
    LeadStatus.QUALIFIED: [LeadStatus.VIEWING_SCHEDULED, LeadStatus.CONVERTED, LeadStatus.LOST],
    LeadStatus.VIEWING_SCHEDULED: [LeadStatus.CONVERTED, LeadStatus.LOST],
    LeadStatus.CONVERTED: [],  # Terminal state
    LeadStatus.LOST: [],  # Terminal state
}


# ============================================================================
# STATUS VALIDATION
# ============================================================================

def can_transition(current_status: LeadStatus, new_status: LeadStatus) -> bool:
    """
    Check if status transition is valid.

    Args:
        current_status: Current lead status
        new_status: Desired new status

    Returns:
        True if transition is allowed
    """
    if current_status == new_status:
        return True

    allowed_statuses = VALID_TRANSITIONS.get(current_status, [])
    return new_status in allowed_statuses


# ============================================================================
# STATUS UPDATE
# ============================================================================

def update_lead_status(
    db: Session,
    lead_id: int,
    new_status: LeadStatus,
    reason: Optional[str] = None,
    changed_by: Optional[int] = None,
    automated: bool = True,
) -> bool:
    """
    Update lead status with validation and history logging.

    Args:
        db: Database session
        lead_id: Lead ID to update
        new_status: New status to set
        reason: Reason for status change
        changed_by: Admin user ID (None if automated)
        automated: True if automated by rules, False if manual

    Returns:
        True if status was updated, False if invalid transition
    """
    # Get lead
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        return False

    old_status = lead.status

    # Check if already at this status
    if old_status == new_status:
        return True

    # Validate transition
    if not can_transition(old_status, new_status):
        return False

    # Update lead status
    lead.status = new_status

    # Log status change
    history = LeadStatusHistory(
        lead_id=lead_id,
        old_status=old_status,
        new_status=new_status,
        changed_by=changed_by,
        automated=1 if automated else 0,
        reason=reason,
    )
    db.add(history)

    db.commit()
    return True


# ============================================================================
# AUTOMATED STATUS PROGRESSION
# ============================================================================

def evaluate_lead_progression(
    db: Session,
    lead: Lead,
    customer_state: dict,
) -> Optional[LeadStatus]:
    """
    Evaluate if lead should progress to next status based on gathered info.

    Business Rules:
    - NEW → WARM: Buy/rent + location OR budget known, 1+ property details viewed
    - WARM → HOT: Viewing/handoff requested OR contact given with <3mo timeline
    - HOT → QUALIFIED: Name + phone/email + buy/rent + budget + location + selected property
    - QUALIFIED → VIEWING_SCHEDULED: Appointment booked

    Args:
        db: Database session
        lead: Lead object
        customer_state: Current customer state dict

    Returns:
        Suggested new status, or None if no change
    """
    current_status = lead.status

    # Terminal states - no progression
    if current_status in [LeadStatus.CONVERTED, LeadStatus.LOST]:
        return None

    # Check progression rules

    # NEW → WARM
    if current_status == LeadStatus.NEW:
        has_location_or_budget = (
            customer_state.get("location") or customer_state.get("budget")
        )
        has_listing_type = customer_state.get("listing_type")
        properties_viewed = customer_state.get("properties_viewed", 0)

        if has_listing_type and has_location_or_budget and properties_viewed >= 1:
            return LeadStatus.WARM

    # WARM → HOT
    if current_status == LeadStatus.WARM:
        requested_viewing = customer_state.get("requested_viewing", False)
        requested_handoff = customer_state.get("requested_handoff", False)
        has_contact = customer_state.get("email") or customer_state.get("phone")
        timeline = customer_state.get("timeline")

        if requested_viewing or requested_handoff:
            return LeadStatus.HOT

        if has_contact and timeline in ["within_1_month", "1-3_months"]:
            return LeadStatus.HOT

    # HOT → QUALIFIED
    if current_status == LeadStatus.HOT:
        has_name = bool(customer_state.get("name"))
        has_contact = bool(customer_state.get("email") or customer_state.get("phone"))
        has_listing_type = bool(customer_state.get("listing_type"))
        has_budget = bool(customer_state.get("budget"))
        has_location = bool(customer_state.get("location"))
        selected_property = customer_state.get("selected_property_id")

        if all([has_name, has_contact, has_listing_type, has_budget, has_location, selected_property]):
            return LeadStatus.QUALIFIED

    # QUALIFIED → VIEWING_SCHEDULED
    if current_status == LeadStatus.QUALIFIED:
        has_appointment = customer_state.get("appointment_booked", False)

        if has_appointment:
            return LeadStatus.VIEWING_SCHEDULED

    return None


def auto_progress_lead(
    db: Session,
    lead_id: int,
    customer_state: dict,
) -> Optional[LeadStatus]:
    """
    Automatically progress lead status if rules are met.

    Args:
        db: Database session
        lead_id: Lead ID
        customer_state: Current customer state

    Returns:
        New status if progressed, None otherwise
    """
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        return None

    suggested_status = evaluate_lead_progression(db, lead, customer_state)

    if suggested_status and suggested_status != lead.status:
        reason = f"Automated progression based on customer state"
        success = update_lead_status(
            db=db,
            lead_id=lead_id,
            new_status=suggested_status,
            reason=reason,
            automated=True,
        )

        if success:
            return suggested_status

    return None


# ============================================================================
# STATUS HISTORY
# ============================================================================

def get_lead_status_history(db: Session, lead_id: int) -> list[LeadStatusHistory]:
    """
    Get complete status history for a lead.

    Args:
        db: Database session
        lead_id: Lead ID

    Returns:
        List of status history records, ordered by time
    """
    return db.query(LeadStatusHistory).filter(
        LeadStatusHistory.lead_id == lead_id
    ).order_by(LeadStatusHistory.changed_at).all()