"""
Tests for the agent loop (Phase 4).
LLM is mocked - no external API calls. Tools execute for real against SQLite.
"""

import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agent.lm_client import RateLimitError
from app.agent.loop import run_agent_loop
from app.core.database import Base
from app.models.property import Property
from app.services.conversation import create_conversation, get_conversation_messages

# ============================================================================
# FIXTURES & HELPERS
# ============================================================================

@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine)
    session = session_local()

    yield session

    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def sample_property(db_session: Session) -> Property:
    """Create a property that search_properties can find."""
    prop = Property(
        reference="LOOP-001",
        title="Marina 2BR Apartment",
        property_type="apartment",
        listing_type="buy",
        price=Decimal("1400000"),
        location="Dubai Marina",
        community="Marina Diamond",
        bedrooms=2,
        bathrooms=2,
        size_sqft=1200,
        description="Great 2BR with marina view",
        availability="available",
        is_demo=1,
    )
    db_session.add(prop)
    db_session.commit()
    return prop


def text_response(text: str, tokens: int = 42) -> dict:
    return {"content": text, "tool_calls": None, "usage": {"total_tokens": tokens}}


def tool_response(name: str, arguments: dict) -> dict:
    return {
        "content": "",
        "tool_calls": [{"id": "call_1", "name": name, "arguments": arguments}],
        "usage": {"total_tokens": 10},
    }


async def collect_events(db, conversation_id, message):
    return [event async for event in run_agent_loop(db, conversation_id, message)]


def event_names(events):
    return [e["event"] for e in events]


# ============================================================================
# TESTS
# ============================================================================

class TestPlainTextFlow:
    """Agent responds with plain text (no tools)."""

    async def test_text_and_done_events(self, db_session):
        conv, _ = create_conversation(db_session)
        with patch("app.agent.loop.LLMClient") as mock_client:
            mock_client.return_value.generate.return_value = text_response(
                "Hello! I can help you find property in Dubai."
            )
            events = await collect_events(db_session, conv.id, "Hi, I need help")

        assert event_names(events) == ["text", "done"]
        assert "Hello!" in events[0]["data"]["text"]
        assert events[0]["data"]["is_final"] is True

    async def test_messages_saved(self, db_session):
        conv, _ = create_conversation(db_session)
        with patch("app.agent.loop.LLMClient") as mock_client:
            mock_client.return_value.generate.return_value = text_response(
                "Sure, what is your budget?"
            )
            await collect_events(db_session, conv.id, "Show me apartments")

        messages = get_conversation_messages(db_session, conv.id)
        assert [m.role for m in messages] == ["user", "assistant"]
        assert messages[0].content == "Show me apartments"
        assert messages[1].content == "Sure, what is your budget?"
        assert messages[1].token_count == 42

    async def test_llm_called_with_user_message(self, db_session):
        conv, _ = create_conversation(db_session)
        with patch("app.agent.loop.LLMClient") as mock_client:
            mock_client.return_value.generate.return_value = text_response("ok")
            await collect_events(db_session, conv.id, "I want a villa")

        call_kwargs = mock_client.return_value.generate.call_args.kwargs
        message_contents = [m["content"] for m in call_kwargs["messages"]]
        assert "I want a villa" in message_contents


class TestToolCallFlow:
    """LLM requests a tool; the loop executes it against real SQLite data."""

    async def test_search_tool_emits_property_cards(self, db_session, sample_property):
        conv, _ = create_conversation(db_session)
        with patch("app.agent.loop.LLMClient") as mock_client:
            mock_client.return_value.generate.side_effect = [
                tool_response(
                    "search_properties",
                    {
                        "listing_type": "buy",
                        "location": "Dubai Marina",
                        "bedrooms": 2,
                        "max_price": 1500000,
                    },
                ),
                text_response("I found 1 property in Dubai Marina for you."),
            ]
            events = await collect_events(
                db_session, conv.id, "2BR in Marina under 1.5M"
            )

        names = event_names(events)
        assert "property_cards" in names
        assert names[-1] == "done"

        cards = next(e for e in events if e["event"] == "property_cards")
        assert cards["data"]["total_found"] == 1
        assert cards["data"]["properties"][0]["location"] == "Dubai Marina"

    async def test_final_text_still_saved_after_tool(self, db_session, sample_property):
        conv, _ = create_conversation(db_session)
        with patch("app.agent.loop.LLMClient") as mock_client:
            mock_client.return_value.generate.side_effect = [
                tool_response(
                    "search_properties",
                    {"listing_type": "buy", "location": "Dubai Marina", "bedrooms": 2},
                ),
                text_response("Here is what I found for you."),
            ]
            await collect_events(db_session, conv.id, "Search Marina")

        messages = get_conversation_messages(db_session, conv.id)
        assert [m.role for m in messages] == ["user", "assistant"]
        assert messages[1].content == "Here is what I found for you."


class TestValidationInLoop:
    """Validation runs on LLM output before streaming."""

    async def test_bad_response_regenerated(self, db_session):
        conv, _ = create_conversation(db_session)
        bad = text_response("This property gives guaranteed returns of 20%!")
        good = text_response("This property has strong rental demand.")
        with patch("app.agent.loop.LLMClient") as mock_client:
            mock_client.return_value.generate.side_effect = [bad, good]
            events = await collect_events(db_session, conv.id, "Tell me about it")

        assert events[0]["data"]["text"] == "This property has strong rental demand."
        messages = get_conversation_messages(db_session, conv.id)
        assert messages[1].content == "This property has strong rental demand."

    async def test_repeated_bad_response_uses_fallback(self, db_session):
        conv, _ = create_conversation(db_session)
        bad = text_response("Amazing! Guaranteed returns, no risk at all.")
        with patch("app.agent.loop.LLMClient") as mock_client:
            mock_client.return_value.generate.side_effect = [bad, bad]
            events = await collect_events(db_session, conv.id, "Sell me this")

        final_text = events[0]["data"]["text"]
        assert "guaranteed" not in final_text.lower()
        assert "apologize" in final_text
        messages = get_conversation_messages(db_session, conv.id)
        assert messages[1].content == final_text


class TestErrorPaths:
    """Configuration and runtime errors produce error events, not crashes."""

    async def test_missing_api_key_configuration_error(self, db_session):
        conv, _ = create_conversation(db_session)
        with patch(
            "app.agent.loop.LLMClient",
            side_effect=ValueError("No LLM API key configured"),
        ):
            events = await collect_events(db_session, conv.id, "hello")

        assert events[0]["event"] == "error"
        assert events[0]["data"]["error_type"] == "configuration_error"
        assert events[0]["data"]["recoverable"] is False
        messages = get_conversation_messages(db_session, conv.id)
        assert messages[0].role == "user"

    async def test_rate_limit_error_event(self, db_session):
        conv, _ = create_conversation(db_session)
        with patch("app.agent.loop.LLMClient") as mock_client:
            mock_client.return_value.generate.side_effect = RateLimitError("slow down")
            events = await collect_events(db_session, conv.id, "hello")

        assert events[0]["event"] == "error"
        assert events[0]["data"]["error_type"] == "rate_limit"
        assert events[0]["data"]["recoverable"] is True

    async def test_generic_exception_error_event(self, db_session):
        conv, _ = create_conversation(db_session)
        with patch("app.agent.loop.LLMClient") as mock_client:
            mock_client.return_value.generate.side_effect = RuntimeError("boom")
            events = await collect_events(db_session, conv.id, "hello")

        assert events[0]["event"] == "error"
        assert events[0]["data"]["error_type"] == "service_unavailable"
        assert events[0]["data"]["recoverable"] is True

    async def test_max_iterations_stops_loop(self, db_session):
        conv, _ = create_conversation(db_session)
        slots_call = tool_response(
            "get_available_slots",
            {"property_id": 1, "date_from": "2026-11-02", "date_to": "2026-11-06"},
        )
        with patch("app.agent.loop.LLMClient") as mock_client:
            mock_client.return_value.generate.side_effect = [slots_call] * 5
            events = await collect_events(db_session, conv.id, "book a viewing")

        last = events[-1]
        assert last["event"] == "error"
        assert last["data"]["error_type"] == "max_iterations"
