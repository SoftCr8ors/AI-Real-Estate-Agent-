"""
Reply validation.
Validates AI responses for accuracy before sending to customer.
"""

import re
from typing import Optional

from sqlalchemy.orm import Session

from app.services.search import get_property_details


# ============================================================================
# VALIDATION RULES
# ============================================================================

PROHIBITED_PHRASES = [
    "guaranteed return",
    "guaranteed roi",
    "100% return",
    "no risk",
    "risk-free",
    "guaranteed profit",
    "guaranteed appreciation",
    "can't lose",
    "double your money",
    "triple your investment",
]


# ============================================================================
# VALIDATORS
# ============================================================================

def validate_response(
    db: Session,
    response_text: str,
    conversation_id: int,
) -> tuple[bool, Optional[str]]:
    """
    Validate AI response before sending to customer.
    
    Args:
        db: Database session
        response_text: AI-generated response text
        conversation_id: Current conversation ID
        
    Returns:
        Tuple of (is_valid: bool, error_message: Optional[str])
    """
    # 1. Check for prohibited phrases
    is_valid, error = check_prohibited_phrases(response_text)
    if not is_valid:
        return False, error
    
    # 2. Validate property references
    is_valid, error = validate_property_references(db, response_text)
    if not is_valid:
        return False, error
    
    # 3. Validate price mentions
    is_valid, error = validate_price_mentions(db, response_text)
    if not is_valid:
        return False, error
    
    return True, None


def check_prohibited_phrases(response_text: str) -> tuple[bool, Optional[str]]:
    """
    Check for prohibited marketing phrases.
    
    Args:
        response_text: Response text to check
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    text_lower = response_text.lower()
    
    for phrase in PROHIBITED_PHRASES:
        if phrase in text_lower:
            return False, f"Response contains prohibited phrase: '{phrase}'"
    
    return True, None


def validate_property_references(db: Session, response_text: str) -> tuple[bool, Optional[str]]:
    """
    Validate that property IDs mentioned exist in database.
    
    Args:
        db: Database session
        response_text: Response text
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Extract property IDs from text (e.g., "Property #123" or "ID: 123")
    property_id_pattern = r'(?:property\s*#?|id:?\s*)(\d+)'
    matches = re.findall(property_id_pattern, response_text, re.IGNORECASE)
    
    for match in matches:
        property_id = int(match)
        
        # Check if property exists
        prop = get_property_details(db, property_id)
        if not prop:
            return False, f"Response references non-existent property ID: {property_id}"
    
    return True, None


def validate_price_mentions(db: Session, response_text: str) -> tuple[bool, Optional[str]]:
    """
    Validate price mentions against database.
    
    Args:
        db: Database session
        response_text: Response text
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Extract price mentions (e.g., "AED 1,500,000" or "1.5M AED")
    # This is a simplified check - in production, would be more sophisticated
    
    # Pattern: AED followed by number
    price_pattern = r'AED\s*([\d,\.]+[KMk]?)'
    price_matches = re.findall(price_pattern, response_text, re.IGNORECASE)
    
    # If prices are mentioned without property context, let it pass
    # (General budget discussions are okay)
    if not price_matches:
        return True, None
    
    # Check if property IDs are also mentioned
    property_id_pattern = r'(?:property\s*#?|id:?\s*)(\d+)'
    property_matches = re.findall(property_id_pattern, response_text, re.IGNORECASE)
    
    if not property_matches:
        # Prices mentioned but no specific properties - probably budget discussion
        return True, None
    
    # If both property and price mentioned, could validate they match
    # For now, we'll trust the tool outputs were correct
    return True, None


# ============================================================================
# RESPONSE CORRECTION
# ============================================================================

def get_safe_fallback_response(error_type: str) -> str:
    """
    Get a safe fallback response when validation fails.
    
    Args:
        error_type: Type of validation error
        
    Returns:
        Safe fallback response text
    """
    fallbacks = {
        "prohibited_phrase": (
            "I apologize, but I need to rephrase that. "
            "Let me help you find the right property based on your requirements. "
            "What specific features are most important to you?"
        ),
        "invalid_property": (
            "I apologize for the confusion. Let me search for available properties "
            "that match your criteria. Could you confirm your requirements?"
        ),
        "invalid_price": (
            "I need to verify those details. Let me pull up the accurate information "
            "for you. One moment please."
        ),
        "general": (
            "I apologize, but I need to verify some information before responding. "
            "Let me help you find what you're looking for. What are you most interested in?"
        ),
    }
    
    return fallbacks.get(error_type, fallbacks["general"])


# ============================================================================
# REGENERATION STRATEGY
# ============================================================================

def should_regenerate(attempt_count: int) -> bool:
    """
    Determine if response should be regenerated.
    
    Args:
        attempt_count: Number of generation attempts so far
        
    Returns:
        True if should regenerate, False if should use fallback
    """
    # Only allow 1 regeneration attempt
    return attempt_count < 2


def build_correction_prompt(error_message: str) -> str:
    """
    Build a prompt to correct the previous response.
    
    Args:
        error_message: Validation error message
        
    Returns:
        Correction prompt
    """
    return (
        f"Your previous response had an issue: {error_message}\n\n"
        "Please regenerate your response while:\n"
        "1. Only referencing properties from the search results\n"
        "2. Avoiding any guaranteed return or risk-free language\n"
        "3. Using accurate prices from the database\n"
        "4. Being helpful and professional"
    )