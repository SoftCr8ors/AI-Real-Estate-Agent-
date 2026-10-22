"""
Tests for Chat API endpoints (Phase 4).
Uses SQLite with dependency override instead of PostgreSQL.
LLM calls are mocked - no external API needed.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import Base, get_db
from app.main import app
from app.services.conversation import add_message, create_conversation


@pytest.fixture(scope="function")
def db_engine():
    """Shared in-memory SQLite engine (StaticPool so all connections see one DB)."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_factory(db_engine):
    """Session factory bound to the test engine."""
    return sessionmaker(bind=db_engine, autoflush=False)


@pytest.fixture(scope="function")
def client(db_factory):
    """TestClient with get_db overridden to SQLite."""

    def override_get_db():
        db = db_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class TestStartConversation:
    """POST /chat/start"""

    def test_start_returns_token_and_id(self, client):
        response = client.post("/chat/start", json={})
        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        assert "session_token" in data
        assert "created_at" in data
        assert isinstance(data["conversation_id"], int)
        assert len(data["session_token"]) > 20

    def test_each_start_creates_new_conversation(self, client):
        first = client.post("/chat/start", json={}).json()
        second = client.post("/chat/start", json={}).json()
        assert first["conversation_id"] != second["conversation_id"]
        assert first["session_token"] != second["session_token"]


class TestSendMessage:
    """POST /chat/message"""

    def test_missing_token_rejected(self, client):
        response = client.post("/chat/message", json={"message": "hello"})
        assert response.status_code == 401

    def test_invalid_token_rejected(self, client):
        response = client.post(
            "/chat/message",
            json={"message": "hello", "session_token": "invalid_token_xyz"},
        )
        assert response.status_code == 401

    def test_ended_conversation_rejected(self, client, db_factory):
        client.post("/chat/start", json={}).json()["session_token"]

        # End the conversation directly in DB
        session = db_factory()
        conv, plain_token = create_conversation(session)
        conv.status = "ended"
        session.commit()
        session.close()

        response = client.post(
            "/chat/message",
            json={"message": "hello", "session_token": plain_token},
        )
        assert response.status_code == 400
        assert "ended" in response.json()["detail"]

    def test_valid_token_streams_sse(self, client):
        token = client.post("/chat/start", json={}).json()["session_token"]

        async def fake_stream(db, conversation_id, user_message):
            yield 'event: text\ndata: {"text": "Hello! How can I help?", "is_final": true}\n\n'
            yield 'event: done\ndata: {}\n\n'

        with patch("app.routers.chat.stream_agent_response", fake_stream):
            response = client.post(
                "/chat/message",
                json={"message": "I want a 2BR in Marina", "session_token": token},
            )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        assert "event: text" in response.text
        assert "event: done" in response.text
        assert "Hello!" in response.text

    def test_missing_message_field_rejected(self, client):
        token = client.post("/chat/start", json={}).json()["session_token"]
        response = client.post(
            "/chat/message", json={"session_token": token}
        )
        assert response.status_code == 422


class TestConversationHistory:
    """GET /chat/history/{conversation_id}"""

    def test_unknown_conversation_404(self, client):
        response = client.get("/chat/history/99999")
        assert response.status_code == 404

    def test_existing_conversation_returns_messages(self, client, db_factory):
        session = db_factory()
        conv, _ = create_conversation(session)
        conv_id = conv.id
        add_message(session, conv_id, role="user", content="I need a 2BR in Marina")
        add_message(
            session,
            conv_id,
            role="assistant",
            content="Great! Let me find options for you.",
            token_count=50,
        )
        session.close()

        response = client.get(f"/chat/history/{conv_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["conversation"]["conversation_id"] == conv_id
        assert data["conversation"]["message_count"] == 2
        assert len(data["messages"]) == 2
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][1]["role"] == "assistant"
        assert data["messages"][1]["content"] == "Great! Let me find options for you."

    def test_history_shows_message_count(self, client, db_factory):
        session = db_factory()
        conv, _ = create_conversation(session)
        conv_id = conv.id
        add_message(session, conv_id, role="user", content="hello")
        session.close()

        response = client.get(f"/chat/history/{conv_id}")
        assert response.json()["conversation"]["message_count"] == 1


class TestChatHealth:
    """GET /chat/health"""

    def test_health_ok(self, client):
        response = client.get("/chat/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "chat"
