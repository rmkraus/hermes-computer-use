"""OpenAI-compatible /v1/chat/completions endpoint backed by the DeepAgent.

Wraps the computer-use DeepAgent in a minimal FastAPI app that speaks
the OpenAI chat completions protocol.  This lets any OpenAI client
(Hermes, LangChain, curl, etc.) drive the desktop agent without knowing
about MCP or LangGraph.
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Hermes Computer Use — OpenAI API",
    description="Ubuntu desktop automation via OpenAI-compatible chat completions",
    version="0.3.0",
)

# Lazy agent cache
_agent_cache: dict[str, Any] = {}


def _get_agent() -> Any:
    if "agent" not in _agent_cache:
        from hermes_computer_use.agent.graph import create_computer_use_agent  # noqa: PLC0415
        _agent_cache["agent"] = create_computer_use_agent()
        logger.info("DeepAgent initialised for OpenAI API")
    return _agent_cache["agent"]


# ---------------------------------------------------------------------------
# Request / response models (OpenAI wire format subset)
# ---------------------------------------------------------------------------


class Message(BaseModel):
    role: str
    content: str | list[Any]


class ChatCompletionRequest(BaseModel):
    model: str = "hermes-computer-use"
    messages: list[Message]
    temperature: float | None = None
    max_tokens: int | None = None
    stream: bool = False


class Choice(BaseModel):
    index: int = 0
    message: Message
    finish_reason: str = "stop"


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:8]}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str = "hermes-computer-use"
    choices: list[Choice]
    usage: Usage = Field(default_factory=Usage)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "hermes-computer-use"}


@app.get("/v1/models")
async def list_models() -> dict[str, Any]:
    """List available models (OpenAI-compatible)."""
    return {
        "object": "list",
        "data": [
            {
                "id": "hermes-computer-use",
                "object": "model",
                "created": 1700000000,
                "owned_by": "hermes",
            }
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest) -> JSONResponse:
    """OpenAI-compatible chat completions endpoint.

    The last user message is treated as the goal for the DeepAgent.
    Previous messages are passed as conversation context.
    """
    if request.stream:
        raise HTTPException(
            status_code=400,
            detail="Streaming is not yet supported by hermes-computer-use.",
        )

    # Extract the user's goal from the last user message
    user_messages = [m for m in request.messages if m.role == "user"]
    if not user_messages:
        raise HTTPException(status_code=400, detail="No user messages in request.")

    # Build input for the agent: include full message history as context
    goal_message = user_messages[-1].content
    if isinstance(goal_message, list):
        # Multi-modal — extract text parts
        goal_message = " ".join(
            p["text"] if isinstance(p, dict) and "text" in p else str(p)
            for p in goal_message
        )

    # Build message history for the agent
    lc_messages = []
    for msg in request.messages:
        content = msg.content if isinstance(msg.content, str) else str(msg.content)
        if msg.role == "system":
            from langchain_core.messages import SystemMessage  # noqa: PLC0415
            lc_messages.append(SystemMessage(content=content))
        elif msg.role == "user":
            from langchain_core.messages import HumanMessage  # noqa: PLC0415
            lc_messages.append(HumanMessage(content=content))
        elif msg.role == "assistant":
            from langchain_core.messages import AIMessage  # noqa: PLC0415
            lc_messages.append(AIMessage(content=content))

    try:
        agent = _get_agent()
        result = agent.invoke({"messages": lc_messages})
        messages = result.get("messages", [])
    except Exception as exc:
        logger.exception("Agent invocation failed")
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}") from exc

    # Extract the final AI response
    ai_response = ""
    for msg in reversed(messages):
        if hasattr(msg, "content") and hasattr(msg, "type") and msg.type == "ai":
            content = msg.content
            if isinstance(content, list):
                ai_response = "\n".join(
                    p["text"] if isinstance(p, dict) and "text" in p else str(p)
                    for p in content
                    if not (isinstance(p, dict) and p.get("type") == "image_url")
                )
            else:
                ai_response = str(content)
            break

    if not ai_response:
        ai_response = "Task completed."

    response = ChatCompletionResponse(
        model=request.model,
        choices=[
            Choice(
                message=Message(role="assistant", content=ai_response),
                finish_reason="stop",
            )
        ],
    )
    return JSONResponse(content=response.model_dump())
