"""
Property schemas for search and responses.
"""

from decimal import Decimal

from pydantic import BaseModel, Field

# ============================================================================
# REQUEST SCHEMAS (What user sends)
# ============================================================================

class PropertySearchRequest(BaseModel):
    """
    Search request from user.
    All fields optional - user can provide any combination.
    """
    listing_type: str | None = Field(None, description="buy or rent")
    location: str | None = Field(None, description="Location/community name")
    property_type: str | None = Field(None, description="apartment, villa, etc.")
    bedrooms: int | None = Field(None, ge=0, description="Number of bedrooms (0=studio)")
    bathrooms: int | None = Field(None, ge=0, description="Number of bathrooms")
    min_price: Decimal | None = Field(None, ge=0, description="Minimum price")
    max_price: Decimal | None = Field(None, ge=0, description="Maximum budget")
    min_size: int | None = Field(None, ge=0, description="Minimum size in sqft")
    max_size: int | None = Field(None, ge=0, description="Maximum size in sqft")
    furnished: bool | None = Field(None, description="Furnished requirement")
    amenities: list[str] | None = Field(None, description="Required amenities")


# ============================================================================
# RESPONSE SCHEMAS (What API returns)
# ============================================================================

class PropertyImageResponse(BaseModel):
    """Single property image."""
    image_url: str
    display_order: int | None = None

    class Config:
        from_attributes = True


class PropertyCardResponse(BaseModel):
    """
    Property card for search results.
    Contains everything needed to display a property card.
    """
    id: int
    reference: str
    title: str
    property_type: str
    listing_type: str

    # Price
    price: Decimal
    currency: str

    # Location
    location: str
    community: str

    # Details
    bedrooms: int
    bathrooms: int
    size_sqft: int
    furnished: bool

    # Search specific
    match_score: float = Field(..., description="Match score 0-100")
    over_budget: bool = Field(False, description="Property is over budget")

    # Metadata
    availability: str
    is_demo: bool

    # Display data
    primary_image: str | None = None
    amenities: list[str] = []

    class Config:
        from_attributes = True


class PropertyDetailResponse(BaseModel):
    """
    Full property details.
    Everything about one property.
    """
    id: int
    reference: str
    title: str
    property_type: str
    listing_type: str

    # Price
    price: Decimal
    currency: str
    rent_period: str | None = None

    # Location
    location: str
    community: str
    latitude: Decimal | None = None
    longitude: Decimal | None = None

    # Details
    bedrooms: int
    bathrooms: int
    size_sqft: int
    furnished: bool

    # Content
    description: str
    listing_url: str | None = None

    # Metadata
    availability: str
    is_demo: bool
    last_updated: str | None = None

    # Related data
    images: list[PropertyImageResponse] = []
    amenities: list[str] = []

    class Config:
        from_attributes = True


class SearchResultsResponse(BaseModel):
    """
    Complete search results with metadata.
    """
    total: int = Field(..., description="Total properties found")
    within_budget: int = Field(..., description="Properties within budget")
    over_budget: int = Field(..., description="Properties over budget")
    properties: list[PropertyCardResponse]
    suggestions: list[str] | None = Field(None, description="Suggestions if no results")


class NoMatchSuggestionsResponse(BaseModel):
    """
    Suggestions when no properties match.
    Based on real data from database.
    """
    message: str
    suggestions: list[str]
    similar_count: int = Field(..., description="How many similar properties exist")
