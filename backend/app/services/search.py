"""
Property search service.
Main search engine that filters, scores, and orders properties.
"""

from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.amenity import Amenity
from app.models.image import PropertyImage
from app.models.property import Property
from app.services.scoring import calculate_match_score


# ============================================================================
# MAIN SEARCH FUNCTION
# ============================================================================

def search_properties(
    db: Session,
    listing_type: Optional[str] = None,
    location: Optional[str] = None,
    property_type: Optional[str] = None,
    bedrooms: Optional[int] = None,
    bathrooms: Optional[int] = None,
    min_price: Optional[Decimal] = None,
    max_price: Optional[Decimal] = None,
    min_size: Optional[int] = None,
    max_size: Optional[int] = None,
    furnished: Optional[bool] = None,
    amenities: Optional[List[str]] = None,
) -> Dict:
    """
    Search properties with filters, scoring, and ordering.
    
    Returns:
        Dictionary with:
        - properties: List of matching properties with scores
        - total: Total count
        - within_budget: Count within budget
        - over_budget: Count over budget
        - suggestions: Suggestions if no results
    """
    # Build base query
    query = db.query(Property)
    
    # CORE FILTERS (Always applied)
    # 1. Only available properties
    query = query.filter(Property.availability == "available")
    
    # 2. Not deleted (soft delete)
    query = query.filter(Property.deleted_at.is_(None))
    
    # SEARCH FILTERS (Based on user input)
    
    # Listing type (buy/rent)
    if listing_type:
        query = query.filter(Property.listing_type == listing_type)
    
    # Location (match location or community)
    if location:
        query = query.filter(
            or_(
                Property.location.ilike(f"%{location}%"),
                Property.community.ilike(f"%{location}%"),
            )
        )
    
    # Property type
    if property_type:
        query = query.filter(Property.property_type == property_type)
    
    # Bedrooms (within one of request)
    if bedrooms is not None:
        query = query.filter(
            and_(
                Property.bedrooms >= bedrooms - 1,
                Property.bedrooms <= bedrooms + 1,
            )
        )
    
    # Bathrooms (at least what they asked for)
    if bathrooms:
        query = query.filter(Property.bathrooms >= bathrooms)
    
    # Price range
    if min_price:
        query = query.filter(Property.price >= min_price)
    
    if max_price:
        # Include properties up to 5% over budget
        budget_with_margin = max_price * Decimal("1.05")
        query = query.filter(Property.price <= budget_with_margin)
    
    # Size range
    if min_size:
        query = query.filter(Property.size_sqft >= min_size)
    
    if max_size:
        query = query.filter(Property.size_sqft <= max_size)
    
    # Furnished
    if furnished is not None:
        furnished_value = 1 if furnished else 0
        query = query.filter(Property.furnished == furnished_value)
    
    # Amenities (properties that have ALL requested amenities)
    if amenities:
        for amenity_name in amenities:
            query = query.join(Property.amenities).filter(
                Amenity.name.ilike(f"%{amenity_name}%")
            )
    
    # Get all matching properties
    properties = query.all()
    
    # If no results, generate suggestions
    if not properties:
        suggestions = generate_suggestions(
            db=db,
            listing_type=listing_type,
            location=location,
            bedrooms=bedrooms,
            max_price=max_price,
        )
        return {
            "properties": [],
            "total": 0,
            "within_budget": 0,
            "over_budget": 0,
            "suggestions": suggestions,
        }
    
    # Calculate scores for each property
    search_criteria = {
        "listing_type": listing_type,
        "location": location,
        "property_type": property_type,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "min_price": min_price,
        "max_price": max_price,
        "min_size": min_size,
        "max_size": max_size,
        "furnished": furnished,
        "amenities": amenities or [],
    }
    
    scored_properties = []
    for prop in properties:
        # Get property data
        property_data = {
            "id": prop.id,
            "reference": prop.reference,
            "title": prop.title,
            "property_type": prop.property_type,
            "listing_type": prop.listing_type,
            "price": prop.price,
            "currency": prop.currency,
            "location": prop.location,
            "community": prop.community,
            "bedrooms": prop.bedrooms,
            "bathrooms": prop.bathrooms,
            "size_sqft": prop.size_sqft,
            "furnished": bool(prop.furnished),
            "availability": prop.availability,
            "is_demo": bool(prop.is_demo),
            "amenities": [a.name for a in prop.amenities],
        }
        
        # Calculate match score
        score = calculate_match_score(property_data, search_criteria)
        
        # Check if over budget
        over_budget = False
        if max_price and prop.price > max_price:
            over_budget = True
        
        # Get primary image
        primary_image = None
        if prop.images:
            # Sort by display_order, take first
            sorted_images = sorted(prop.images, key=lambda x: x.display_order or 999)
            if sorted_images:
                primary_image = sorted_images[0].image_url
        
        scored_properties.append({
            "property": prop,
            "property_data": property_data,
            "score": score,
            "over_budget": over_budget,
            "primary_image": primary_image,
        })
    
    # Sort properties
    # 1. Within budget first, then over budget
    # 2. By score (descending)
    # 3. By price (ascending)
    sorted_properties = sorted(
        scored_properties,
        key=lambda x: (
            x["over_budget"],  # False (within budget) comes first
            -x["score"],  # Higher score first
            float(x["property"].price),  # Lower price first
        ),
    )
    
    # Count within/over budget
    within_budget = sum(1 for p in sorted_properties if not p["over_budget"])
    over_budget_count = len(sorted_properties) - within_budget
    
    return {
        "properties": sorted_properties,
        "total": len(sorted_properties),
        "within_budget": within_budget,
        "over_budget": over_budget_count,
        "suggestions": None,
    }


# ============================================================================
# SUGGESTIONS WHEN NO MATCH
# ============================================================================

def generate_suggestions(
    db: Session,
    listing_type: Optional[str],
    location: Optional[str],
    bedrooms: Optional[int],
    max_price: Optional[Decimal],
) -> List[str]:
    """
    Generate suggestions based on real data when no properties match.
    
    Returns:
        List of suggestion strings
    """
    suggestions = []
    
    # Base query - only available, not deleted
    base_query = db.query(Property).filter(
        Property.availability == "available",
        Property.deleted_at.is_(None),
    )
    
    if listing_type:
        base_query = base_query.filter(Property.listing_type == listing_type)
    
    # Suggestion 1: Higher budget
    if max_price and location:
        # Find properties in same location just above budget
        higher_price_query = base_query.filter(
            or_(
                Property.location.ilike(f"%{location}%"),
                Property.community.ilike(f"%{location}%"),
            )
        ).filter(Property.price > max_price)
        
        if bedrooms is not None:
            higher_price_query = higher_price_query.filter(
                and_(
                    Property.bedrooms >= bedrooms - 1,
                    Property.bedrooms <= bedrooms + 1,
                )
            )
        
        higher_price_count = higher_price_query.count()
        
        if higher_price_count > 0:
            # Find average price of these properties
            avg_price = db.query(Property.price).filter(
                Property.id.in_([p.id for p in higher_price_query.limit(10).all()])
            ).first()
            
            if avg_price and avg_price[0]:
                suggested_budget = int(float(avg_price[0]) * 1.1)  # Add 10% buffer
                suggestions.append(
                    f"Try increasing your budget to AED {suggested_budget:,}. "
                    f"Found {higher_price_count} similar properties in {location}."
                )
    
    # Suggestion 2: Fewer bedrooms
    if bedrooms and bedrooms > 0 and location:
        fewer_bedrooms_query = base_query.filter(
            or_(
                Property.location.ilike(f"%{location}%"),
                Property.community.ilike(f"%{location}%"),
            )
        ).filter(Property.bedrooms == bedrooms - 1)
        
        if max_price:
            fewer_bedrooms_query = fewer_bedrooms_query.filter(
                Property.price <= max_price
            )
        
        fewer_bedrooms_count = fewer_bedrooms_query.count()
        
        if fewer_bedrooms_count > 0:
            suggestions.append(
                f"Consider {bedrooms - 1} bedroom properties in {location}. "
                f"Found {fewer_bedrooms_count} options within your budget."
            )
    
    # Suggestion 3: Nearby areas
    if location:
        nearby_areas = get_nearby_areas(location)
        
        for nearby in nearby_areas:
            nearby_query = base_query.filter(
                or_(
                    Property.location.ilike(f"%{nearby}%"),
                    Property.community.ilike(f"%{nearby}%"),
                )
            )
            
            if bedrooms is not None:
                nearby_query = nearby_query.filter(
                    and_(
                        Property.bedrooms >= bedrooms - 1,
                        Property.bedrooms <= bedrooms + 1,
                    )
                )
            
            if max_price:
                nearby_query = nearby_query.filter(Property.price <= max_price)
            
            nearby_count = nearby_query.count()
            
            if nearby_count > 0:
                suggestions.append(
                    f"Check {nearby} area (near {location}). "
                    f"Found {nearby_count} matching properties."
                )
                break  # Only suggest one nearby area
    
    # Suggestion 4: General availability
    if not suggestions:
        total_available = base_query.count()
        suggestions.append(
            f"We have {total_available} available properties. "
            "Try adjusting your search criteria."
        )
    
    return suggestions[:3]  # Return max 3 suggestions


# ============================================================================
# NEARBY AREAS MAPPING
# ============================================================================

def get_nearby_areas(location: str) -> List[str]:
    """
    Get nearby areas for a location.
    
    This can be extended to use a database table in future.
    """
    location_lower = location.lower()
    
    nearby_map = {
        "dubai marina": ["Jumeirah Lake Towers", "Jumeirah Beach Residence"],
        "jlt": ["Dubai Marina", "Business Bay"],
        "jumeirah lake towers": ["Dubai Marina", "Business Bay"],
        "jvc": ["Dubai Sports City", "Motor City"],
        "jumeirah village circle": ["Dubai Sports City", "Motor City"],
        "downtown dubai": ["Business Bay", "DIFC"],
        "business bay": ["Downtown Dubai", "DIFC"],
        "jbr": ["Dubai Marina", "Palm Jumeirah"],
        "jumeirah beach residence": ["Dubai Marina", "Palm Jumeirah"],
    }
    
    for key, areas in nearby_map.items():
        if key in location_lower:
            return areas
    
    return []


# ============================================================================
# GET PROPERTY DETAILS
# ============================================================================

def get_property_details(db: Session, property_id: int) -> Optional[Property]:
    """
    Get full property details by ID.
    
    Args:
        db: Database session
        property_id: Property ID
    
    Returns:
        Property object or None
    """
    return db.query(Property).filter(
        Property.id == property_id,
        Property.deleted_at.is_(None),  # Not deleted
    ).first()


# ============================================================================
# CHECK AVAILABILITY
# ============================================================================

def check_property_availability(db: Session, property_id: int) -> Optional[str]:
    """
    Check live property availability status.
    
    Args:
        db: Database session
        property_id: Property ID
    
    Returns:
        Availability status or None if not found
    """
    property_obj = db.query(Property).filter(
        Property.id == property_id,
        Property.deleted_at.is_(None),
    ).first()
    
    if property_obj:
        return property_obj.availability
    
    return None