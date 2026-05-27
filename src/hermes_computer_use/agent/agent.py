"""NAT entrypoint for the Ubuntu desktop automation agent.

This module is referenced by workflow.yaml as:

    workflow:
      _type: langgraph_wrapper
      graph: src/hermes_computer_use/agent/agent.py:agent

NAT imports this module at startup, calls SyncBuilder.current().get_llm()
to inject the LLM configured in workflow.yaml, then wraps the resulting
CompiledStateGraph in the full NAT serving stack (streaming, OpenAI-compat
endpoint, MCP, telemetry, eval).
"""
from __future__ import annotations

from deepagents import create_deep_agent
from nat.builder.framework_enum import LLMFrameworkEnum
from nat.builder.sync_builder import SyncBuilder

from hermes_computer_use.agent.tools import TOOLS

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

# NAT calls SyncBuilder.current().get_llm() at module import time to inject
# whichever LLM is declared in workflow.yaml under llms.agent.
model = SyncBuilder.current().get_llm("agent", wrapper_type=LLMFrameworkEnum.LANGCHAIN)

agent = create_deep_agent(
    model=model,
    tools=TOOLS,
    system_prompt=SYSTEM_PROMPT,
)
