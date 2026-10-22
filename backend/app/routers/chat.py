"""
Chat API router.
Endpoints for starting conversations and sending messages via SSE.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.channels.web import stream_agent_response
from app.core.database import get_db
from app.schemas.chat import (
    ChatMessageRequest,
    ConversationHistoryResponse,
    ConversationResponse,
    MessageResponse,
    StartConversationRequest,
    StartConversationResponse,
)
from app.services.conversation import (
    create_conversation,
    get_conversation_by_id,
    get_conversation_by_token,
    get_conversation_messages,
)

router = APIRouter(prefix="/chat", tags=["chat"])


# ============================================================================
# START CONVERSATION
# ============================================================================

@router.post("/start", response_model=StartConversationResponse)
def start_conversation(
    request: StartConversationRequest,
    db: Session = Depends(get_db),
):
    """
    Start a new conversation and get a session token.
    
    Args:
        request: Start conversation request
        db: Database session
        
    Returns:
        StartConversationResponse with conversation_id and session_token
    """
    # Create conversation
    conversation, session_token = create_conversation(
        db=db,
        customer_id=None,  # Anonymous by default
        channel="web",
    )
    
    return StartConversationResponse(
        conversation_id=conversation.id,
        session_token=session_token,
        created_at=conversation.created_at,
    )


# ============================================================================
# SEND MESSAGE (SSE STREAMING)
# ============================================================================

@router.post("/message")
async def send_message(
    request: ChatMessageRequest,
    db: Session = Depends(get_db),
):
    """
    Send a message and stream AI response via SSE.
    
    Args:
        request: Chat message request with session_token
        db: Database session
        
    Returns:
        StreamingResponse with SSE events
    """
    # Validate session token
    if not request.session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token required",
        )
    
    # Get conversation by token
    conversation = get_conversation_by_token(db, request.session_token)
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token",
        )
    
    # Check conversation status
    if conversation.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Conversation is {conversation.status}",
        )
    
    # Stream agent response
    return StreamingResponse(
        stream_agent_response(
            db=db,
            conversation_id=conversation.id,
            user_message=request.message,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


# ============================================================================
# GET CONVERSATION HISTORY (ADMIN/DEBUG)
# ============================================================================

@router.get("/history/{conversation_id}", response_model=ConversationHistoryResponse)
def get_conversation_history(
    conversation_id: int,
    db: Session = Depends(get_db),
):
    """
    Get full conversation history (admin/debug endpoint).
    
    Args:
        conversation_id: Conversation ID
        db: Database session
        
    Returns:
        ConversationHistoryResponse with messages
    """
    # Get conversation
    conversation = get_conversation_by_id(db, conversation_id)
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    
    # Get messages
    messages = get_conversation_messages(db, conversation_id)
    
    # Build response
    conversation_response = ConversationResponse(
        conversation_id=conversation.id,
        customer_id=conversation.customer_id,
        customer_name=conversation.customer_name,
        customer_email=conversation.customer_email,
        status=conversation.status,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=len(messages),
    )
    
    message_responses = [
        MessageResponse(
            message_id=msg.id,
            conversation_id=msg.conversation_id,
            role=msg.role,
            content=msg.content,
            created_at=msg.created_at,
            metadata=None,
        )
        for msg in messages
    ]
    
    return ConversationHistoryResponse(
        conversation=conversation_response,
        messages=message_responses,
    )


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health")
def chat_health_check():
    """
    Health check endpoint for chat API.
    
    Returns:
        Status dict
    """
    return {
        "status": "healthy",
        "service": "chat",
        "version": "1.0.0",
    }
