"""
Property API endpoints.
Public endpoints for property search and details.
"""


from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.properties import (
    PropertyCardResponse,
    PropertyDetailResponse,
    PropertyImageResponse,
    SearchResultsResponse,
)
from app.services import normalize, search

router = APIRouter(prefix="/properties", tags=["properties"])


# ============================================================================
# SEARCH PROPERTIES
# ============================================================================

@router.get("/search", response_model=SearchResultsResponse)
def search_properties_endpoint(
    # Search parameters
    listing_type: str | None = Query(None, description="buy or rent"),
    location: str | None = Query(None, description="Location or community"),
    property_type: str | None = Query(None, description="apartment, villa, etc."),
    bedrooms: int | None = Query(None, ge=0, description="Number of bedrooms"),
    bathrooms: int | None = Query(None, ge=0, description="Number of bathrooms"),
    min_price: str | None = Query(None, description="Minimum price (e.g., 500000, 1.5M)"),
    max_price: str | None = Query(None, description="Maximum price (e.g., 1500000, 1.5M)"),
    min_size: int | None = Query(None, ge=0, description="Minimum size in sqft"),
    max_size: int | None = Query(None, ge=0, description="Maximum size in sqft"),
    furnished: bool | None = Query(None, description="Furnished requirement"),
    amenities: str | None = Query(None, description="Comma-separated amenities"),
    db: Session = Depends(get_db),
):
    """
    Search properties with filters.

    All parameters are optional. System will:
    - Normalize input (1.5M → 1500000, marina → Dubai Marina)
    - Filter available properties only
    - Calculate match scores
    - Order by: within budget first, then score, then price
    - Suggest alternatives if no match

    Example:
        /properties/search?listing_type=buy&location=marina&bedrooms=2&max_price=1.5M
    """
    # Normalize inputs
    normalized_listing_type = normalize.normalize_listing_type(listing_type)
    normalized_location = normalize.normalize_location(location)
    normalized_property_type = normalize.normalize_property_type(property_type)

    # Normalize budget
    normalized_min_price = None
    normalized_max_price = None

    if min_price:
        normalized_min_price = normalize.normalize_budget(min_price)

    if max_price:
        normalized_max_price = normalize.normalize_budget(max_price)

        # If rent and looks monthly, convert to yearly
        if normalized_listing_type == "rent" and normalized_max_price:
            normalized_max_price = normalize.normalize_rent_period(
                normalized_max_price, "monthly"
            )

    # Normalize amenities
    amenity_list = None
    if amenities:
        amenity_list = normalize.normalize_amenities(
            [a.strip() for a in amenities.split(",")]
        )

    # Special case: If budget without buy/rent, suggest to specify
    if normalized_max_price and not normalized_listing_type:
        raise HTTPException(
            status_code=400,
            detail="Please specify if you want to buy or rent. "
            "Use listing_type=buy or listing_type=rent",
        )

    # Search
    results = search.search_properties(
        db=db,
        listing_type=normalized_listing_type,
        location=normalized_location,
        property_type=normalized_property_type,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        min_price=normalized_min_price,
        max_price=normalized_max_price,
        min_size=min_size,
        max_size=max_size,
        furnished=furnished,
        amenities=amenity_list,
    )

    # If no results, return suggestions
    if results["total"] == 0:
        return SearchResultsResponse(
            total=0,
            within_budget=0,
            over_budget=0,
            properties=[],
            suggestions=results.get("suggestions"),
        )

    # Format properties for response
    property_cards = []

    for item in results["properties"]:
        prop = item["property"]

        # Format amenities (limit to 5 for card display)
        amenity_names = [a.name for a in prop.amenities][:5]

        card = PropertyCardResponse(
            id=prop.id,
            reference=prop.reference,
            title=prop.title,
            property_type=prop.property_type,
            listing_type=prop.listing_type,
            price=prop.price,
            currency=prop.currency,
            location=prop.location,
            community=prop.community,
            bedrooms=prop.bedrooms,
            bathrooms=prop.bathrooms,
            size_sqft=prop.size_sqft,
            furnished=bool(prop.furnished),
            match_score=item["score"],
            over_budget=item["over_budget"],
            availability=prop.availability,
            is_demo=bool(prop.is_demo),
            primary_image=item["primary_image"],
            amenities=amenity_names,
        )

        property_cards.append(card)

    return SearchResultsResponse(
        total=results["total"],
        within_budget=results["within_budget"],
        over_budget=results["over_budget"],
        properties=property_cards,
        suggestions=None,
    )


# ============================================================================
# GET PROPERTY DETAILS
# ============================================================================

@router.get("/{property_id}", response_model=PropertyDetailResponse)
def get_property_details_endpoint(
    property_id: int,
    db: Session = Depends(get_db),
):
    """
    Get full details of a specific property.

    Returns all information about the property including:
    - All images
    - All amenities
    - Full description
    - Current availability
    """
    property_obj = search.get_property_details(db, property_id)

    if not property_obj:
        raise HTTPException(status_code=404, detail="Property not found")

    # Format images
    images = [
        PropertyImageResponse(image_url=img.image_url, display_order=img.display_order)
        for img in sorted(property_obj.images, key=lambda x: x.display_order or 999)
    ]

    # Format amenities
    amenity_names = [a.name for a in property_obj.amenities]

    return PropertyDetailResponse(
        id=property_obj.id,
        reference=property_obj.reference,
        title=property_obj.title,
        property_type=property_obj.property_type,
        listing_type=property_obj.listing_type,
        price=property_obj.price,
        currency=property_obj.currency,
        rent_period=property_obj.rent_period if property_obj.rent_period else None,
        location=property_obj.location,
        community=property_obj.community,
        latitude=property_obj.latitude,
        longitude=property_obj.longitude,
        bedrooms=property_obj.bedrooms,
        bathrooms=property_obj.bathrooms,
        size_sqft=property_obj.size_sqft,
        furnished=bool(property_obj.furnished),
        description=property_obj.description,
        listing_url=property_obj.listing_url,
        availability=property_obj.availability,
        is_demo=bool(property_obj.is_demo),
        last_updated=property_obj.last_updated.isoformat() if property_obj.last_updated else None,
        images=images,
        amenities=amenity_names,
    )


# ============================================================================
# CHECK AVAILABILITY
# ============================================================================

@router.get("/{property_id}/availability")
def check_availability_endpoint(
    property_id: int,
    db: Session = Depends(get_db),
):
    """
    Check live availability status of a property.

    Returns the current availability status from database.
    Changes made by admin are reflected immediately.
    """
    availability = search.check_property_availability(db, property_id)

    if availability is None:
        raise HTTPException(status_code=404, detail="Property not found")

    return {
        "property_id": property_id,
        "availability": availability,
        "is_available": availability == "available",
    }
