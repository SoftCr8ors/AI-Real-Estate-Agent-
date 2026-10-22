"""
Settings service - manage encrypted admin settings (AI provider keys).
Handles encryption/decryption of sensitive values like API keys.
"""

from typing import Optional

from sqlalchemy.orm import Session

from app.core.crypto import crypto_service
from app.models.settings import AppSettings


# ============================================================================
# SETTINGS CRUD
# ============================================================================

def get_setting(
    db: Session,
    key: str,
    decrypt: bool = True
) -> Optional[str]:
    """
    Get a setting value by key.

    Args:
        db: Database session
        key: Setting key (e.g., "ai_provider", "gemini_api_key")
        decrypt: If True, decrypt encrypted values

    Returns:
        Setting value (decrypted if encrypted), or None if not found
    """
    setting = db.query(AppSettings).filter(AppSettings.key == key).first()

    if not setting:
        return None

    value = setting.value

    # Decrypt if needed
    if decrypt and setting.is_encrypted and value:
        try:
            value = crypto_service.decrypt(value)
        except Exception as e:
            # Log error but don't crash
            print(f"Failed to decrypt setting '{key}': {e}")
            return None

    return value


def set_setting(
    db: Session,
    key: str,
    value: str,
    encrypt: bool = False,
    category: str = "general",
    description: Optional[str] = None,
    updated_by: Optional[int] = None
) -> AppSettings:
    """
    Set or update a setting value.

    Args:
        db: Database session
        key: Setting key
        value: Setting value (will be encrypted if encrypt=True)
        encrypt: Whether to encrypt the value
        category: Setting category (ai_provider, email, general)
        description: Human-readable description
        updated_by: Admin user ID making the change

    Returns:
        Created or updated AppSettings instance
    """
    # Encrypt if needed
    if encrypt and value:
        value = crypto_service.encrypt(value)

    # Check if setting exists
    setting = db.query(AppSettings).filter(AppSettings.key == key).first()

    if setting:
        # Update existing
        setting.value = value
        setting.is_encrypted = 1 if encrypt else 0
        setting.category = category
        if description:
            setting.description = description
        setting.updated_by = updated_by
    else:
        # Create new
        setting = AppSettings(
            key=key,
            value=value,
            is_encrypted=1 if encrypt else 0,
            category=category,
            description=description,
            updated_by=updated_by
        )
        db.add(setting)

    db.commit()
    db.refresh(setting)
    return setting


def delete_setting(db: Session, key: str) -> bool:
    """
    Delete a setting by key.

    Args:
        db: Database session
        key: Setting key to delete

    Returns:
        True if deleted, False if not found
    """
    setting = db.query(AppSettings).filter(AppSettings.key == key).first()
    if setting:
        db.delete(setting)
        db.commit()
        return True
    return False


# ============================================================================
# AI PROVIDER SETTINGS
# ============================================================================

def get_ai_provider(db: Session) -> str:
    """
    Get the currently configured AI provider.

    Returns:
        "gemini", "groq", "openai", or value from config/env
    """
    provider = get_setting(db, "ai_provider", decrypt=False)
    if provider:
        return provider
    
    # Fall back to environment/config
    from app.core.config import settings
    return settings.AI_PROVIDER


def get_ai_api_key(db: Session, provider: Optional[str] = None) -> Optional[str]:
    """
    Get API key for specified provider (or current provider).
    Priority: database (encrypted) > environment variable

    Args:
        db: Database session
        provider: Provider name (gemini/groq/openai), or None for current

    Returns:
        Decrypted API key, or None if not found
    """
    if not provider:
        provider = get_ai_provider(db)

    # Try database first (admin-saved, encrypted)
    key_name = f"{provider}_api_key"
    api_key = get_setting(db, key_name, decrypt=True)

    if api_key:
        return api_key

    # Fall back to config/environment
    from app.core.config import settings
    
    if provider == "gemini":
        return settings.GEMINI_API_KEY
    elif provider == "groq":
        return settings.GROQ_API_KEY
    elif provider == "openai":
        return settings.OPENAI_API_KEY

    return None


def set_ai_provider(
    db: Session,
    provider: str,
    api_key: Optional[str] = None,
    updated_by: Optional[int] = None
) -> None:
    """
    Set AI provider and optionally its API key.

    Args:
        db: Database session
        provider: "gemini", "groq", or "openai"
        api_key: API key to encrypt and store (optional)
        updated_by: Admin user ID
    """
    # Set provider
    set_setting(
        db,
        key="ai_provider",
        value=provider,
        encrypt=False,
        category="ai_provider",
        description="Current AI provider for chat agent",
        updated_by=updated_by
    )

    # Set API key if provided
    if api_key:
        key_name = f"{provider}_api_key"
        set_setting(
            db,
            key=key_name,
            value=api_key,
            encrypt=True,
            category="ai_provider",
            description=f"API key for {provider.title()}",
            updated_by=updated_by
        )