"""
Tool schemas for AI agent function calling.
These define the strict input/output contracts for all 9 tools.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ============================================================================
# SEARCH TOOLS
# ============================================================================

class SearchPropertiesInput(BaseModel):
    """Input for search_properties tool"""
    listing_type: Optional[str] = Field(None, description="'buy' or 'rent'")
    location: Optional[str] = Field(None, description="City, area, or neighborhood name")
    min_price: Optional[float] = Field(None, description="Minimum price in AED")
    max_price: Optional[float] = Field(None, description="Maximum price in AED")
    bedrooms: Optional[int] = Field(None, description="Number of bedrooms")
    property_type: Optional[str] = Field(None, description="'apartment', 'villa', 'townhouse', 'penthouse'")
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
    properties: List[PropertySummary]
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
    amenities: List[str]
    images: List[str]  # URLs
    agent_name: Optional[str]
    agent_phone: Optional[str]


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
    customer_id: Optional[int] = None
    requirements: Optional[str] = Field(None, description="JSON string of customer requirements")
    notes: Optional[str] = None


class CreateLeadOutput(BaseModel):
    """Output from create_lead tool"""
    lead_id: int
    status: str
    created: bool  # True if new, False if already existed


class UpdateLeadInput(BaseModel):
    """Input for update_lead tool"""
    lead_id: int
    status: Optional[LeadStatusEnum] = None
    requirements: Optional[str] = None
    notes: Optional[str] = None
    expected_timeline: Optional[str] = None


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
    slots: List[TimeSlot]


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
    customer_email: Optional[str] = None


class BookViewingOutput(BaseModel):
    """Output from book_viewing tool"""
    booking_id: int
    confirmed: bool
    slot_datetime: datetime
    confirmation_sent: bool


# ============================================================================
# CUSTOMER HISTORY
# ============================================================================

class GetCustomerHistoryInput(BaseModel):
    """Input for get_customer_history tool"""
    customer_id: Optional[int] = None
    conversation_id: Optional[int] = None


class CustomerInteraction(BaseModel):
    """Single customer interaction record"""
    date: datetime
    type: str  # "viewed", "interested", "contacted"
    property_id: Optional[int]
    property_title: Optional[str]
    notes: Optional[str]


class GetCustomerHistoryOutput(BaseModel):
    """Output from get_customer_history tool"""
    customer_id: Optional[int]
    total_conversations: int
    total_properties_viewed: int
    interactions: List[CustomerInteraction]
    current_lead_status: Optional[str]


# ============================================================================
# SALES NOTIFICATION (STUB)
# ============================================================================

class NotifySalesTeamInput(BaseModel):
    """Input for notify_sales_team tool"""
    lead_id: int
    urgency: str = Field("normal", description="'low', 'normal', 'high', 'urgent'")
    message: Optional[str] = None


class NotifySalesTeamOutput(BaseModel):
    """Output from notify_sales_team tool"""
    notification_sent: bool
    notified_agents: List[str]
    notification_id: str