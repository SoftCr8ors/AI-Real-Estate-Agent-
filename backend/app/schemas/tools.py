"""
Tool schemas for AI agent function calling.
These define the strict input/output contracts for all 9 tools.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

# ============================================================================
# SEARCH TOOLS
# ============================================================================

class SearchPropertiesInput(BaseModel):
    """Input for search_properties tool"""
    listing_type: str | None = Field(None, description="'buy' or 'rent'")
    location: str | None = Field(None, description="City, area, or neighborhood name")
    min_price: float | None = Field(None, description="Minimum price in AED")
    max_price: float | None = Field(None, description="Maximum price in AED")
    bedrooms: int | None = Field(None, description="Number of bedrooms")
    property_type: str | None = Field(None, description="'apartment', 'villa', 'townhouse', 'penthouse'")
    limit: int = Field(10, description="Max results to return", ge=1, le=50)


class PropertySummary(BaseModel):
    """Single property in search results"""
    property_id: int
    title: str
    location: str
    price: float
    bedrooms: int
    bathrooms: int
    area_sqft: int
    listing_type: str
    property_type: str
    relevance_score: int  # 0-100


class SearchPropertiesOutput(BaseModel):
    """Output from search_properties tool"""
    properties: list[PropertySummary]
    total_found: int
    query_understood: str  # Natural language summary of what was searched


# ============================================================================
# PROPERTY DETAILS
# ============================================================================

class GetPropertyDetailsInput(BaseModel):
    """Input for get_property_details tool"""
    property_id: int = Field(..., description="The property ID to fetch details for")


class PropertyDetails(BaseModel):
    """Full property information"""
    property_id: int
    title: str
    description: str
    location: str
    price: float
    bedrooms: int
    bathrooms: int
    area_sqft: int
    listing_type: str
    property_type: str
    availability: str
    amenities: list[str]
    images: list[str]  # URLs
    agent_name: str | None
    agent_phone: str | None


class GetPropertyDetailsOutput(BaseModel):
    """Output from get_property_details tool"""
    property: PropertyDetails
    availability_status: str  # "available", "under_offer", "sold"


# ============================================================================
# AVAILABILITY CHECK
# ============================================================================

class CheckAvailabilityInput(BaseModel):
    """Input for check_property_availability tool"""
    property_id: int = Field(..., description="Property ID to check")


class CheckAvailabilityOutput(BaseModel):
    """Output from check_property_availability tool"""
    property_id: int
    available: bool
    status: str  # "available", "under_offer", "sold"
    last_updated: datetime


# ============================================================================
# LEAD MANAGEMENT
# ============================================================================

class LeadStatusEnum(str, Enum):
    NEW = "new"
    WARM = "warm"
    HOT = "hot"
    QUALIFIED = "qualified"
    VIEWING_SCHEDULED = "viewing_scheduled"


class CreateLeadInput(BaseModel):
    """Input for create_lead tool"""
    conversation_id: int
    customer_id: int | None = None
    requirements: str | None = Field(None, description="JSON string of customer requirements")
    notes: str | None = None


class CreateLeadOutput(BaseModel):
    """Output from create_lead tool"""
    lead_id: int
    status: str
    created: bool  # True if new, False if already existed


class UpdateLeadInput(BaseModel):
    """Input for update_lead tool"""
    lead_id: int
    status: LeadStatusEnum | None = None
    requirements: str | None = None
    notes: str | None = None
    expected_timeline: str | None = None


class UpdateLeadOutput(BaseModel):
    """Output from update_lead tool"""
    lead_id: int
    old_status: str
    new_status: str
    updated: bool


# ============================================================================
# VIEWING SLOTS (STUB)
# ============================================================================

class GetAvailableSlotsInput(BaseModel):
    """Input for get_available_slots tool"""
    property_id: int
    date_from: str = Field(..., description="Start date YYYY-MM-DD")
    date_to: str = Field(..., description="End date YYYY-MM-DD")


class TimeSlot(BaseModel):
    """A single viewing time slot"""
    slot_id: str
    datetime: datetime
    available: bool


class GetAvailableSlotsOutput(BaseModel):
    """Output from get_available_slots tool"""
    property_id: int
    slots: list[TimeSlot]


# ============================================================================
# BOOKING (STUB)
# ============================================================================

class BookViewingInput(BaseModel):
    """Input for book_viewing tool"""
    lead_id: int
    property_id: int
    slot_id: str
    customer_name: str
    customer_phone: str
    customer_email: str | None = None


class BookViewingOutput(BaseModel):
    """Output from book_viewing tool"""
    booking_id: int
    confirmed: bool
    slot_datetime: datetime
    confirmation_sent: bool
    message: str | None = None


# ============================================================================
# CUSTOMER HISTORY
# ============================================================================

class GetCustomerHistoryInput(BaseModel):
    """Input for get_customer_history tool"""
    customer_id: int | None = None
    conversation_id: int | None = None


class CustomerInteraction(BaseModel):
    """Single customer interaction record"""
    date: datetime
    type: str  # "viewed", "interested", "contacted"
    property_id: int | None
    property_title: str | None
    notes: str | None


class GetCustomerHistoryOutput(BaseModel):
    """Output from get_customer_history tool"""
    customer_id: int | None
    total_conversations: int
    total_properties_viewed: int
    interactions: list[CustomerInteraction]
    current_lead_status: str | None


# ============================================================================
# SALES NOTIFICATION (STUB)
# ============================================================================

class NotifySalesTeamInput(BaseModel):
    """Input for notify_sales_team tool"""
    lead_id: int
    urgency: str = Field("normal", description="'low', 'normal', 'high', 'urgent'")
    message: str | None = None


class NotifySalesTeamOutput(BaseModel):
    """Output from notify_sales_team tool"""
    notification_sent: bool
    notified_agents: list[str]
    notification_id: str
