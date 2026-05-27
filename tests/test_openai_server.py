"""Tests for the OpenAI-compatible API server.

All tests use TestClient (no real network, no real LLM).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    from hermes_computer_use.server.openai_server import app
    return TestClient(app)


@pytest.fixture()
def mock_agent():
    """Return a mock CompiledStateGraph that echoes the last user message."""
    from langchain_core.messages import AIMessage

    agent = MagicMock()
    agent.invoke.return_value = {
        "messages": [
            MagicMock(type="ai", content="I clicked the button."),
        ]
    }
    return agent


class TestHealthEndpoint:
    def test_health_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestModelsEndpoint:
    def test_lists_model(self, client):
        resp = client.get("/v1/models")
        assert resp.status_code == 200
        data = resp.json()
        ids = [m["id"] for m in data["data"]]
        assert "hermes-computer-use" in ids


class TestChatCompletions:
    def test_basic_request(self, client, mock_agent):
        with patch(
            "hermes_computer_use.server.openai_server._get_agent",
            return_value=mock_agent,
        ):
            resp = client.post(
                "/v1/chat/completions",
                json={
                    "model": "hermes-computer-use",
                    "messages": [{"role": "user", "content": "Take a screenshot"}],
                },
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["object"] == "chat.completion"
        assert len(body["choices"]) == 1
        assert body["choices"][0]["message"]["role"] == "assistant"
        assert "button" in body["choices"][0]["message"]["content"]

    def test_no_user_messages_returns_400(self, client):
        resp = client.post(
            "/v1/chat/completions",
            json={
                "model": "hermes-computer-use",
                "messages": [{"role": "system", "content": "You are a helper"}],
            },
        )
        assert resp.status_code == 400

    def test_streaming_returns_400(self, client):
        resp = client.post(
            "/v1/chat/completions",
            json={
                "model": "hermes-computer-use",
                "messages": [{"role": "user", "content": "Do something"}],
                "stream": True,
            },
        )
        assert resp.status_code == 400

    def test_agent_error_returns_500(self, client):
        bad_agent = MagicMock()
        bad_agent.invoke.side_effect = RuntimeError("LLM unavailable")
        with patch(
            "hermes_computer_use.server.openai_server._get_agent",
            return_value=bad_agent,
        ):
            resp = client.post(
                "/v1/chat/completions",
                json={
                    "messages": [{"role": "user", "content": "Click something"}],
                },
            )
        assert resp.status_code == 500

    def test_response_has_id_and_created(self, client, mock_agent):
        with patch(
            "hermes_computer_use.server.openai_server._get_agent",
            return_value=mock_agent,
        ):
            resp = client.post(
                "/v1/chat/completions",
                json={"messages": [{"role": "user", "content": "Hello"}]},
            )
        body = resp.json()
        assert body["id"].startswith("chatcmpl-")
        assert isinstance(body["created"], int)

    def test_system_and_user_messages(self, client, mock_agent):
        """Multi-turn messages should be accepted without error."""
        with patch(
            "hermes_computer_use.server.openai_server._get_agent",
            return_value=mock_agent,
        ):
            resp = client.post(
                "/v1/chat/completions",
                json={
                    "messages": [
                        {"role": "system", "content": "Be helpful."},
                        {"role": "user", "content": "Open Firefox"},
                        {"role": "assistant", "content": "Opening Firefox..."},
                        {"role": "user", "content": "Now go to example.com"},
                    ]
                },
            )
        assert resp.status_code == 200

    def test_empty_agent_response_returns_task_completed(self, client):
        """If agent returns no messages, return a fallback string."""
        empty_agent = MagicMock()
        empty_agent.invoke.return_value = {"messages": []}
        with patch(
            "hermes_computer_use.server.openai_server._get_agent",
            return_value=empty_agent,
        ):
            resp = client.post(
                "/v1/chat/completions",
                json={"messages": [{"role": "user", "content": "Do it"}]},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert "completed" in body["choices"][0]["message"]["content"].lower()
