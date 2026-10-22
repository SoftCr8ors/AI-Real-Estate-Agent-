"""
Channels package - handles different communication channels (web, whatsapp, etc).
"""

from app.channels.web import stream_agent_response

__all__ = ["stream_agent_response"]