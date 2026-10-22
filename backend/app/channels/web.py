"""
Web channel - SSE streaming for browser-based chat.
Handles Server-Sent Events streaming from agent to frontend.
"""

import asyncio
import json
from typing import AsyncGenerator

from sqlalchemy.orm import Session

from app.agent.loop import run_agent_loop


# ============================================================================
# SSE STREAMING
# ============================================================================

async def stream_agent_response(
    db: Session,
    conversation_id: int,
    user_message: str,
) -> AsyncGenerator[str, None]:
    """
    Stream agent response as Server-Sent Events.
    
    Args:
        db: Database session
        conversation_id: Conversation ID
        user_message: User's message
        
    Yields:
        SSE formatted strings (event: type\ndata: json\n\n)
    """
    done_sent = False
    try:
        # Run agent loop and stream events
        async for event in run_agent_loop(db, conversation_id, user_message):
            # Format as SSE
            sse_message = format_sse_event(
                event_type=event["event"],
                data=event["data"],
            )
            if event["event"] == "done":
                done_sent = True
            yield sse_message

            # Small delay to prevent overwhelming client
            await asyncio.sleep(0.01)

    except Exception as e:
        # Send error event
        error_event = {
            "event": "error",
            "data": {
                "error_type": "internal_error",
                "message": "An unexpected error occurred. Please try again.",
                "recoverable": True,
            }
        }
        yield format_sse_event(error_event["event"], error_event["data"])

    finally:
        # Only send done if agent loop didn't already send one
        if not done_sent:
            yield format_sse_event("done", {})


def format_sse_event(event_type: str, data: dict) -> str:
    """
    Format event as SSE string.
    
    Args:
        event_type: Event type (text, property_cards, error, etc.)
        data: Event data dict
        
    Returns:
        SSE formatted string
    """
    # Convert data to JSON
    data_json = json.dumps(data, default=str)
    
    # Format as SSE
    # Format: event: <type>\ndata: <json>\n\n
    sse = f"event: {event_type}\ndata: {data_json}\n\n"
    
    return sse


# ============================================================================
# CHUNKED TEXT STREAMING (FUTURE)
# ============================================================================

async def stream_text_chunks(
    text: str,
    chunk_size: int = 20,
    delay: float = 0.05,
) -> AsyncGenerator[dict, None]:
    """
    Stream text in chunks for typing effect (future enhancement).
    
    Args:
        text: Full text to stream
        chunk_size: Characters per chunk
        delay: Delay between chunks in seconds
        
    Yields:
        Text chunk events
    """
    words = text.split()
    current_chunk = []
    
    for word in words:
        current_chunk.append(word)
        
        # Send chunk when size reached
        if len(" ".join(current_chunk)) >= chunk_size:
            yield {
                "event": "text",
                "data": {
                    "text": " ".join(current_chunk) + " ",
                    "is_final": False,
                }
            }
            current_chunk = []
            await asyncio.sleep(delay)
    
    # Send remaining chunk
    if current_chunk:
        yield {
            "event": "text",
            "data": {
                "text": " ".join(current_chunk),
                "is_final": True,
            }
        }


# ============================================================================
# CONNECTION MANAGEMENT (FUTURE)
# ============================================================================

class ConnectionManager:
    """
    Manage active SSE connections (future enhancement for multi-user support).
    """
    
    def __init__(self):
        self.active_connections: dict[int, list] = {}
    
    def connect(self, conversation_id: int, connection):
        """Add a connection."""
        if conversation_id not in self.active_connections:
            self.active_connections[conversation_id] = []
        self.active_connections[conversation_id].append(connection)
    
    def disconnect(self, conversation_id: int, connection):
        """Remove a connection."""
        if conversation_id in self.active_connections:
            self.active_connections[conversation_id].remove(connection)
            if not self.active_connections[conversation_id]:
                del self.active_connections[conversation_id]
    
    def get_connections(self, conversation_id: int) -> list:
        """Get all connections for a conversation."""
        return self.active_connections.get(conversation_id, [])


# Global connection manager (for future use)
connection_manager = ConnectionManager()