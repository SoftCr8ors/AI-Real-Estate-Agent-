"""
Chat API schemas for SSE streaming and conversation management.
Defines all event types the frontend can receive.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class ChatMessageRequest(BaseModel):
    """Request to send a message in a conversation"""
    message: str = Field(..., min_length=1, max_length=1000, description="User's message")
    session_token: str | None = Field(None, description="Secret session token (identifies conversation securely)")
    metadata: dict[str, Any] | None = Field(None, description="Extra context (referrer, campaign, etc.)")


class StartConversationRequest(BaseModel):
    """
    Request to start a new conversation.
    Returns a session_token that must be used for all subsequent messages.
    """
    initial_message: str | None = Field(None, max_length=1000)
    metadata: dict[str, Any] | None = None


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
    data: dict[str, Any]
    message_id: int | None = None


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
    image_url: str | None
    relevance_score: int


class PropertyCardsEvent(BaseModel):
    """Property search results event"""
    properties: list[PropertyCard]
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
    amenities: list[str]
    images: list[str]
    agent_name: str | None
    agent_phone: str | None


class NoMatchSuggestion(BaseModel):
    """Alternative suggestion"""
    reason: str
    suggestion: str
    adjusted_criteria: dict[str, Any] | None


class NoMatchSuggestionsEvent(BaseModel):
    """Suggestions when no properties match"""
    original_query: str
    suggestions: list[NoMatchSuggestion]


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
    slots: list[TimeSlotOption]


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
    current_value: str | None = None


class ContactFormRequestEvent(BaseModel):
    """Request customer contact information"""
    reason: str  # "To schedule a viewing, we need your contact details"
    fields: list[ContactFormField]
    lead_id: int | None


class HandoffEvent(BaseModel):
    """Transfer to human agent"""
    reason: str
    urgency: str  # "low", "normal", "high"
    estimated_wait_time: str | None
    lead_id: int | None


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
    customer_id: int | None
    customer_name: str | None
    customer_email: str | None
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
    metadata: dict[str, Any] | None


class ConversationHistoryResponse(BaseModel):
    """Full conversation history (admin only)"""
    conversation: ConversationResponse
    messages: list[MessageResponse]


class ConversationListResponse(BaseModel):
    """List of conversations (admin only)"""
    conversations: list[ConversationResponse]
    total: int
    page: int
    page_size: int
