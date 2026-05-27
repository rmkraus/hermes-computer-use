"""DeepAgent graph factory for Ubuntu computer-use.

Creates a ``create_deep_agent``-powered LangGraph CompiledStateGraph
pre-loaded with all computer-use tools.  The graph is model-agnostic:
pass any ``langchain_core.language_models.BaseChatModel`` instance.
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

from hermes_computer_use.agent.tools import get_computer_use_tools
from hermes_computer_use.safety.checker import SafetyChecker

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from langgraph.graph.state import CompiledStateGraph

SYSTEM_PROMPT = """\
You are a Ubuntu desktop automation agent. You control a real Ubuntu desktop
using screenshot, mouse, keyboard, window-management, and shell tools.

## Workflow
1. Take a screenshot to understand the current desktop state.
2. Plan the steps needed to accomplish the user's goal.
3. Execute each step: click, type, run commands, manage windows.
4. After each significant action, take a new screenshot to verify the result.
5. Report back with what you did and the current state.

## Guidelines
- Always screenshot first before acting — never assume the desktop state.
- Use zoom_region to read small text or inspect UI elements closely.
- Prefer keyboard shortcuts over clicking when faster (e.g. Ctrl+C, Ctrl+V).
- Use run_command for tasks that are easier done in a terminal.
- If something fails, take a screenshot to diagnose before retrying.
- Be cautious with destructive operations — confirm before deleting files.
"""


def create_computer_use_agent(
    model: "BaseChatModel | str | None" = None,
    safety_checker: SafetyChecker | None = None,
    system_prompt: str | None = None,
    **kwargs,
) -> "CompiledStateGraph":
    """Create a DeepAgent graph equipped with Ubuntu desktop automation tools.

    Args:
        model: LangChain chat model instance, or a model string in
               ``"provider:model_name"`` format (e.g.
               ``"openai:gpt-4o"`` or ``"nvidia:meta/llama-3.1-70b-instruct"``).
               Defaults to ``COMPUTER_USE_MODEL`` env var, then
               ``"openai:gpt-4o"``.
        safety_checker: Override the default ``SafetyChecker``.
        system_prompt: Override the default system prompt.
        **kwargs: Extra keyword arguments forwarded to ``create_deep_agent``.

    Returns:
        A compiled LangGraph ``CompiledStateGraph`` ready to ``.invoke()``
        or ``.stream()``.
    """
    from deepagents import create_deep_agent  # noqa: PLC0415

    # Resolve model
    if model is None:
        model = os.environ.get("COMPUTER_USE_MODEL", "openai:gpt-4o")
    if isinstance(model, str):
        from langchain.chat_models import init_chat_model  # noqa: PLC0415
        model = init_chat_model(model)

    tools = get_computer_use_tools(safety_checker=safety_checker)
    prompt = system_prompt or SYSTEM_PROMPT

    return create_deep_agent(
        model=model,
        tools=tools,
        system_prompt=prompt,
        **kwargs,
    )
