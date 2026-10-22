"""
Chat API schemas for SSE streaming and conversation management.
Defines all event types the frontend can receive.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class ChatMessageRequest(BaseModel):
    """Request to send a message in a conversation"""
    message: str = Field(..., min_length=1, max_length=1000, description="User's message")
    session_token: Optional[str] = Field(None, description="Secret session token (identifies conversation securely)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Extra context (referrer, campaign, etc.)")


class StartConversationRequest(BaseModel):
    """
    Request to start a new conversation.
    Returns a session_token that must be used for all subsequent messages.
    """
    initial_message: Optional[str] = Field(None, max_length=1000)
    metadata: Optional[Dict[str, Any]] = None


# ============================================================================
# SSE EVENT TYPES
# ============================================================================

class SSEEventType(str, Enum):
    """All possible SSE event types the agent can stream"""
    TEXT = "text"                                    # Streaming text chunk
    PROPERTY_CARDS = "property_cards"                # Property search results
    PROPERTY_DETAILS = "property_details"            # Single property full details
    NO_MATCH_SUGGESTIONS = "no_match_suggestions"    # Alternative suggestions when no results
    TIME_SLOTS = "time_slots"                        # Available viewing slots
    APPOINTMENT = "appointment"                      # Booking confirmation
    CONTACT_FORM_REQUEST = "contact_form_request"    # Ask for contact info
    HANDOFF = "handoff"                              # Transfer to human agent
    ERROR = "error"                                  # Error message
    DONE = "done"                                    # Stream complete


# ============================================================================
# SSE EVENT PAYLOADS
# ============================================================================

class SSEEvent(BaseModel):
    """Base SSE event structure"""
    event: SSEEventType
    data: Dict[str, Any]
    message_id: Optional[int] = None


class TextChunk(BaseModel):
    """Streaming text chunk"""
    text: str
    is_final: bool = False


class PropertyCard(BaseModel):
    """Property card for search results"""
    property_id: int
    title: str
    location: str
    price: float
    bedrooms: int
    bathrooms: int
    area_sqft: int
    image_url: Optional[str]
    relevance_score: int


class PropertyCardsEvent(BaseModel):
    """Property search results event"""
    properties: List[PropertyCard]
    total_found: int
    query_summary: str


class PropertyDetailsEvent(BaseModel):
    """Full property details event"""
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
    images: List[str]
    agent_name: Optional[str]
    agent_phone: Optional[str]


class NoMatchSuggestion(BaseModel):
    """Alternative suggestion"""
    reason: str
    suggestion: str
    adjusted_criteria: Optional[Dict[str, Any]]


class NoMatchSuggestionsEvent(BaseModel):
    """Suggestions when no properties match"""
    original_query: str
    suggestions: List[NoMatchSuggestion]


class TimeSlotOption(BaseModel):
    """A viewing time slot"""
    slot_id: str
    datetime: datetime
    available: bool
    label: str  # "Tomorrow at 2 PM"


class TimeSlotsEvent(BaseModel):
    """Available viewing slots"""
    property_id: int
    property_title: str
    slots: List[TimeSlotOption]


class AppointmentEvent(BaseModel):
    """Booking confirmation"""
    booking_id: int
    property_id: int
    property_title: str
    slot_datetime: datetime
    customer_name: str
    confirmation_sent: bool


class ContactFormField(BaseModel):
    """A form field to collect"""
    field_name: str  # "name", "email", "phone"
    label: str
    required: bool
    current_value: Optional[str] = None


class ContactFormRequestEvent(BaseModel):
    """Request customer contact information"""
    reason: str  # "To schedule a viewing, we need your contact details"
    fields: List[ContactFormField]
    lead_id: Optional[int]


class HandoffEvent(BaseModel):
    """Transfer to human agent"""
    reason: str
    urgency: str  # "low", "normal", "high"
    estimated_wait_time: Optional[str]
    lead_id: Optional[int]


class ErrorEvent(BaseModel):
    """Error occurred"""
    error_type: str  # "rate_limit", "service_unavailable", "validation_error"
    message: str  # User-friendly message
    recoverable: bool


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class StartConversationResponse(BaseModel):
    """Response when starting a new conversation"""
    conversation_id: int
    session_token: str  # Secret token - store in browser, send with every message
    created_at: datetime


class ConversationResponse(BaseModel):
    """Conversation metadata (for admin panel only - no session_token exposed)"""
    conversation_id: int
    customer_id: Optional[int]
    customer_name: Optional[str]
    customer_email: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    message_count: int


class MessageResponse(BaseModel):
    """Single message in conversation history"""
    message_id: int
    conversation_id: int
    role: str  # "user" or "assistant"
    content: str
    created_at: datetime
    metadata: Optional[Dict[str, Any]]


class ConversationHistoryResponse(BaseModel):
    """Full conversation history (admin only)"""
    conversation: ConversationResponse
    messages: List[MessageResponse]


class ConversationListResponse(BaseModel):
    """List of conversations (admin only)"""
    conversations: List[ConversationResponse]
    total: int
    page: int
    page_size: int