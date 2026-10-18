"""
Property schemas for search and responses.
"""

from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


# ============================================================================
# REQUEST SCHEMAS (What user sends)
# ============================================================================

class PropertySearchRequest(BaseModel):
    """
    Search request from user.
    All fields optional - user can provide any combination.
    """
    listing_type: Optional[str] = Field(None, description="buy or rent")
    location: Optional[str] = Field(None, description="Location/community name")
    property_type: Optional[str] = Field(None, description="apartment, villa, etc.")
    bedrooms: Optional[int] = Field(None, ge=0, description="Number of bedrooms (0=studio)")
    bathrooms: Optional[int] = Field(None, ge=0, description="Number of bathrooms")
    min_price: Optional[Decimal] = Field(None, ge=0, description="Minimum price")
    max_price: Optional[Decimal] = Field(None, ge=0, description="Maximum budget")
    min_size: Optional[int] = Field(None, ge=0, description="Minimum size in sqft")
    max_size: Optional[int] = Field(None, ge=0, description="Maximum size in sqft")
    furnished: Optional[bool] = Field(None, description="Furnished requirement")
    amenities: Optional[List[str]] = Field(None, description="Required amenities")


# ============================================================================
# RESPONSE SCHEMAS (What API returns)
# ============================================================================

class PropertyImageResponse(BaseModel):
    """Single property image."""
    image_url: str
    display_order: Optional[int] = None
    
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
    primary_image: Optional[str] = None
    amenities: List[str] = []
    
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
    rent_period: Optional[str] = None
    
    # Location
    location: str
    community: str
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    
    # Details
    bedrooms: int
    bathrooms: int
    size_sqft: int
    furnished: bool
    
    # Content
    description: str
    listing_url: Optional[str] = None
    
    # Metadata
    availability: str
    is_demo: bool
    last_updated: Optional[str] = None
    
    # Related data
    images: List[PropertyImageResponse] = []
    amenities: List[str] = []
    
    class Config:
        from_attributes = True


class SearchResultsResponse(BaseModel):
    """
    Complete search results with metadata.
    """
    total: int = Field(..., description="Total properties found")
    within_budget: int = Field(..., description="Properties within budget")
    over_budget: int = Field(..., description="Properties over budget")
    properties: List[PropertyCardResponse]
    suggestions: Optional[List[str]] = Field(None, description="Suggestions if no results")


class NoMatchSuggestionsResponse(BaseModel):
    """
    Suggestions when no properties match.
    Based on real data from database.
    """
    message: str
    suggestions: List[str]
    similar_count: int = Field(..., description="How many similar properties exist")