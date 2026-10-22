"""
Conversation service - manage chat sessions and messages.
Handles conversation state, message history, and session tokens.
"""

import hashlib
import json
import secrets
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.message import Message


# ============================================================================
# SESSION TOKEN MANAGEMENT
# ============================================================================

def generate_session_token() -> str:
    """
    Generate a secure random session token.
    
    Returns:
        Random token string (32 characters)
    """
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    """
    Hash a session token for storage.
    
    Args:
        token: Plain session token
        
    Returns:
        SHA256 hash of token
    """
    return hashlib.sha256(token.encode()).hexdigest()


# ============================================================================
# CONVERSATION CREATION
# ============================================================================

def create_conversation(
    db: Session,
    customer_id: Optional[int] = None,
    channel: str = "web",
) -> tuple[Conversation, str]:
    """
    Create a new conversation session.
    
    Args:
        db: Database session
        customer_id: Customer ID (None for anonymous)
        channel: Channel (web, whatsapp, etc.)
        
    Returns:
        Tuple of (Conversation object, plain session_token)
    """
    # Generate session token
    plain_token = generate_session_token()
    hashed_token = hash_session_token(plain_token)
    
    # Create conversation
    conversation = Conversation(
        session_id=hashed_token,
        customer_id=customer_id,
        channel=channel,
        status="active",
        customer_state=None,
        state_summary=None,
    )
    
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    
    return conversation, plain_token


# ============================================================================
# CONVERSATION RETRIEVAL
# ============================================================================

def get_conversation_by_token(
    db: Session,
    session_token: str,
) -> Optional[Conversation]:
    """
    Get conversation by session token.
    
    Args:
        db: Database session
        session_token: Plain session token from client
        
    Returns:
        Conversation object or None if not found or invalid
    """
    # Hash the token
    hashed_token = hash_session_token(session_token)
    
    # Find conversation
    conversation = db.query(Conversation).filter(
        Conversation.session_id == hashed_token
    ).first()
    
    return conversation


def get_conversation_by_id(
    db: Session,
    conversation_id: int,
) -> Optional[Conversation]:
    """
    Get conversation by ID (admin use only).
    
    Args:
        db: Database session
        conversation_id: Conversation ID
        
    Returns:
        Conversation object or None
    """
    return db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()


# ============================================================================
# CONVERSATION STATE MANAGEMENT
# ============================================================================

def update_conversation_state(
    db: Session,
    conversation_id: int,
    customer_state: dict,
    state_summary: Optional[str] = None,
) -> Optional[Conversation]:
    """
    Update conversation customer state.
    
    Args:
        db: Database session
        conversation_id: Conversation ID
        customer_state: Customer state dict
        state_summary: Summary of known/unknown info
        
    Returns:
        Updated Conversation or None if not found
    """
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()
    
    if not conversation:
        return None
    
    # Store state as JSON string
    conversation.customer_state = json.dumps(customer_state)
    
    if state_summary is not None:
        conversation.state_summary = state_summary
    
    db.commit()
    db.refresh(conversation)
    
    return conversation


def get_conversation_state(
    db: Session,
    conversation_id: int,
) -> dict:
    """
    Get customer state from conversation.
    
    Args:
        db: Database session
        conversation_id: Conversation ID
        
    Returns:
        Customer state dict (empty if not found)
    """
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()
    
    if not conversation or not conversation.customer_state:
        return {}
    
    try:
        return json.loads(conversation.customer_state)
    except (json.JSONDecodeError, TypeError):
        return {}


def update_customer_info(
    db: Session,
    conversation_id: int,
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
) -> Optional[Conversation]:
    """
    Update customer contact information in conversation.
    
    Args:
        db: Database session
        conversation_id: Conversation ID
        name: Customer name
        email: Customer email
        phone: Customer phone
        
    Returns:
        Updated Conversation or None if not found
    """
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()
    
    if not conversation:
        return None
    
    # Update fields if provided
    if name is not None:
        conversation.customer_name = name
    
    if email is not None:
        conversation.customer_email = email
    
    if phone is not None:
        conversation.customer_phone = phone
    
    db.commit()
    db.refresh(conversation)
    
    return conversation


# ============================================================================
# MESSAGE MANAGEMENT
# ============================================================================

def add_message(
    db: Session,
    conversation_id: int,
    role: str,
    content: str,
    metadata_json: Optional[str] = None,
    token_count: Optional[int] = None,
    status: str = "completed",
) -> Message:
    """
    Add a message to conversation.
    
    Args:
        db: Database session
        conversation_id: Conversation ID
        role: "user" or "assistant"
        content: Message content
        metadata_json: Optional metadata JSON string
        token_count: Token count for cost tracking
        status: Message status (completed, streaming, error)
        
    Returns:
        Created Message object
    """
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        metadata_json=metadata_json,
        token_count=token_count,
        status=status,
    )
    
    db.add(message)
    db.commit()
    db.refresh(message)
    
    return message


def get_conversation_messages(
    db: Session,
    conversation_id: int,
    limit: Optional[int] = None,
    offset: int = 0,
) -> list[Message]:
    """
    Get messages from conversation, ordered by time.
    
    Args:
        db: Database session
        conversation_id: Conversation ID
        limit: Max messages to return (None for all)
        offset: Skip first N messages
        
    Returns:
        List of Message objects
    """
    query = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at)
    
    if offset:
        query = query.offset(offset)
    
    if limit:
        query = query.limit(limit)
    
    return query.all()


def get_recent_messages(
    db: Session,
    conversation_id: int,
    count: int = 12,
) -> list[Message]:
    """
    Get the most recent N messages from conversation.
    
    Args:
        db: Database session
        conversation_id: Conversation ID
        count: Number of recent messages (default 12 for AI context)
        
    Returns:
        List of Message objects (oldest to newest)
    """
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at.desc()).limit(count).all()
    
    # Reverse to get chronological order
    return list(reversed(messages))


def get_message_count(
    db: Session,
    conversation_id: int,
) -> int:
    """
    Get total message count in conversation.
    
    Args:
        db: Database session
        conversation_id: Conversation ID
        
    Returns:
        Message count
    """
    return db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).count()


# ============================================================================
# CONVERSATION STATUS
# ============================================================================

def end_conversation(
    db: Session,
    conversation_id: int,
    reason: str = "user_ended",
) -> Optional[Conversation]:
    """
    End a conversation session.
    
    Args:
        db: Database session
        conversation_id: Conversation ID
        reason: Reason for ending (user_ended, timeout, transferred)
        
    Returns:
        Updated Conversation or None if not found
    """
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()
    
    if not conversation:
        return None
    
    conversation.status = "ended"
    conversation.ended_at = datetime.utcnow()
    
    db.commit()
    db.refresh(conversation)
    
    return conversation


def transfer_conversation(
    db: Session,
    conversation_id: int,
    notes: Optional[str] = None,
) -> Optional[Conversation]:
    """
    Transfer conversation to human agent.
    
    Args:
        db: Database session
        conversation_id: Conversation ID
        notes: Transfer notes
        
    Returns:
        Updated Conversation or None if not found
    """
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()
    
    if not conversation:
        return None
    
    conversation.status = "transferred"
    
    db.commit()
    db.refresh(conversation)
    
    return conversation


# ============================================================================
# CONVERSATION LISTING (ADMIN)
# ============================================================================

def list_conversations(
    db: Session,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Conversation]:
    """
    List conversations (admin use).
    
    Args:
        db: Database session
        status: Filter by status (active, ended, transferred)
        limit: Max results
        offset: Pagination offset
        
    Returns:
        List of Conversation objects
    """
    query = db.query(Conversation)
    
    if status:
        query = query.filter(Conversation.status == status)
    
    return query.order_by(
        Conversation.updated_at.desc()
    ).offset(offset).limit(limit).all()


def get_active_conversations_count(db: Session) -> int:
    """
    Get count of active conversations.
    
    Args:
        db: Database session
        
    Returns:
        Count of active conversations
    """
    return db.query(Conversation).filter(
        Conversation.status == "active"
    ).count()