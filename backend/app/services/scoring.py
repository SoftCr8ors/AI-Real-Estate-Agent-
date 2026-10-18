"""
Property scoring service.
Calculates match scores (0-100) based on user criteria.
"""

from decimal import Decimal

# ============================================================================
# BASE WEIGHTS (When all criteria provided)
# ============================================================================

BASE_WEIGHTS = {
    "location": 25,
    "budget": 20,
    "bedrooms": 15,
    "amenities": 15,
    "property_type": 10,
    "bathrooms": 5,
    "size": 5,
    "furnished": 5,
}


# ============================================================================
# SCORE CALCULATION
# ============================================================================

def calculate_match_score(
    property_data: dict,
    search_criteria: dict,
) -> float:
    """
    Calculate match score (0-100) for a property.

    Weights are renormalized based on what criteria the user actually provided.

    Args:
        property_data: Property details from database
        search_criteria: User's search criteria

    Returns:
        Match score between 0 and 100
    """
    scores = {}
    active_weights = {}

    # Calculate individual scores for criteria that were provided

    # 1. LOCATION SCORE
    if search_criteria.get("location"):
        location_score = score_location(
            property_location=property_data.get("location"),
            property_community=property_data.get("community"),
            search_location=search_criteria["location"],
        )
        scores["location"] = location_score
        active_weights["location"] = BASE_WEIGHTS["location"]

    # 2. BUDGET SCORE
    if search_criteria.get("max_price"):
        budget_score = score_budget(
            property_price=property_data.get("price"),
            max_budget=search_criteria["max_price"],
        )
        scores["budget"] = budget_score
        active_weights["budget"] = BASE_WEIGHTS["budget"]

    # 3. BEDROOMS SCORE
    if search_criteria.get("bedrooms") is not None:
        bedroom_score = score_bedrooms(
            property_bedrooms=property_data.get("bedrooms"),
            search_bedrooms=search_criteria["bedrooms"],
        )
        scores["bedrooms"] = bedroom_score
        active_weights["bedrooms"] = BASE_WEIGHTS["bedrooms"]

    # 4. AMENITIES SCORE
    if search_criteria.get("amenities"):
        amenity_score = score_amenities(
            property_amenities=property_data.get("amenities", []),
            search_amenities=search_criteria["amenities"],
        )
        scores["amenities"] = amenity_score
        active_weights["amenities"] = BASE_WEIGHTS["amenities"]

    # 5. PROPERTY TYPE SCORE
    if search_criteria.get("property_type"):
        type_score = score_property_type(
            property_type=property_data.get("property_type"),
            search_type=search_criteria["property_type"],
        )
        scores["property_type"] = type_score
        active_weights["property_type"] = BASE_WEIGHTS["property_type"]

    # 6. BATHROOMS SCORE
    if search_criteria.get("bathrooms"):
        bathroom_score = score_bathrooms(
            property_bathrooms=property_data.get("bathrooms"),
            search_bathrooms=search_criteria["bathrooms"],
        )
        scores["bathrooms"] = bathroom_score
        active_weights["bathrooms"] = BASE_WEIGHTS["bathrooms"]

    # 7. SIZE SCORE
    if search_criteria.get("min_size") or search_criteria.get("max_size"):
        size_score = score_size(
            property_size=property_data.get("size_sqft"),
            min_size=search_criteria.get("min_size"),
            max_size=search_criteria.get("max_size"),
        )
        scores["size"] = size_score
        active_weights["size"] = BASE_WEIGHTS["size"]

    # 8. FURNISHED SCORE
    if search_criteria.get("furnished") is not None:
        furnished_score = score_furnished(
            property_furnished=property_data.get("furnished"),
            search_furnished=search_criteria["furnished"],
        )
        scores["furnished"] = furnished_score
        active_weights["furnished"] = BASE_WEIGHTS["furnished"]

    # Renormalize weights based on active criteria
    total_active_weight = sum(active_weights.values())
    if total_active_weight == 0:
        return 50.0  # Default score if no criteria

    normalized_weights = {
        key: (weight / total_active_weight) * 100
        for key, weight in active_weights.items()
    }

    # Calculate final weighted score
    final_score = sum(
        scores[key] * (normalized_weights[key] / 100)
        for key in scores
    )

    return round(final_score, 2)


# ============================================================================
# INDIVIDUAL SCORING FUNCTIONS
# ============================================================================

def score_location(
    property_location: str | None,
    property_community: str | None,
    search_location: str,
) -> float:
    """
    Score location match.

    Returns:
        100 if exact match, 0 if no match
    """
    if not property_location:
        return 0.0

    search_lower = search_location.lower()
    location_lower = property_location.lower()
    community_lower = (property_community or "").lower()

    # Exact match on location or community
    if search_lower in location_lower or search_lower in community_lower:
        return 100.0

    # Partial match
    if any(word in location_lower or word in community_lower for word in search_lower.split()):
        return 50.0

    return 0.0


def score_budget(property_price: Decimal | None, max_budget: Decimal) -> float:
    """
    Score budget match.

    Returns:
        100 if within budget
        Reduced score if over budget (up to 5% over)
        0 if way over budget
    """
    if not property_price:
        return 0.0

    price_float = float(property_price)
    budget_float = float(max_budget)

    # Within budget
    if price_float <= budget_float:
        return 100.0

    # Over budget but within 5%
    over_percentage = ((price_float - budget_float) / budget_float) * 100

    if over_percentage <= 5:
        # Reduced score: 100 at budget, 50 at 5% over
        return max(50.0, 100.0 - (over_percentage * 10))

    # Way over budget
    return 0.0


def score_bedrooms(property_bedrooms: int | None, search_bedrooms: int) -> float:
    """
    Score bedroom match.

    Returns:
        100 if exact match or within 1
        50 if within 2
        0 otherwise
    """
    if property_bedrooms is None:
        return 0.0

    diff = abs(property_bedrooms - search_bedrooms)

    if diff == 0:
        return 100.0
    elif diff == 1:
        return 100.0  # Within one is acceptable
    elif diff == 2:
        return 50.0
    else:
        return 0.0


def score_amenities(
    property_amenities: list[str],
    search_amenities: list[str],
) -> float:
    """
    Score amenity match.

    Returns:
        100 if all amenities present
        Percentage based on how many match
    """
    if not search_amenities:
        return 100.0

    if not property_amenities:
        return 0.0

    # Normalize to lowercase for comparison
    property_amenities_lower = [a.lower() for a in property_amenities]
    search_amenities_lower = [a.lower() for a in search_amenities]

    # Count matches
    matches = sum(
        1 for amenity in search_amenities_lower
        if any(amenity in prop_amenity for prop_amenity in property_amenities_lower)
    )

    return (matches / len(search_amenities_lower)) * 100


def score_property_type(
    property_type: str | None,
    search_type: str,
) -> float:
    """
    Score property type match.

    Returns:
        100 if exact match, 0 otherwise
    """
    if not property_type:
        return 0.0

    if property_type.lower() == search_type.lower():
        return 100.0

    return 0.0


def score_bathrooms(property_bathrooms: int | None, search_bathrooms: int) -> float:
    """
    Score bathroom match.

    Returns:
        100 if exact match or more
        50 if one less
        0 if two or more less
    """
    if property_bathrooms is None:
        return 0.0

    diff = property_bathrooms - search_bathrooms

    if diff >= 0:
        return 100.0  # Same or more bathrooms is good
    elif diff == -1:
        return 50.0  # One less is acceptable
    else:
        return 0.0  # Two or more less is not good


def score_size(
    property_size: int | None,
    min_size: int | None,
    max_size: int | None,
) -> float:
    """
    Score size match.

    Returns:
        100 if within range
        0 if outside range
    """
    if property_size is None:
        return 0.0

    # Check min
    if min_size and property_size < min_size:
        return 0.0

    # Check max
    if max_size and property_size > max_size:
        return 0.0

    return 100.0


def score_furnished(property_furnished: bool | None, search_furnished: bool) -> float:
    """
    Score furnished status match.

    Returns:
        100 if match, 50 if not specified, 0 if mismatch
    """
    if property_furnished is None:
        return 50.0  # Unknown furnished status

    # Convert int to bool if needed (database uses 0/1)
    if isinstance(property_furnished, int):
        property_furnished = bool(property_furnished)

    if property_furnished == search_furnished:
        return 100.0

    return 0.0
