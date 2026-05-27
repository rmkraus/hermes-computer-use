"""Tests for agent/agent.py — the NAT langgraph_wrapper entrypoint.

Verifies that the module correctly wires SyncBuilder → DeepAgent without
requiring a real NAT server, real display, or real LLM credentials.
We mock NAT and deepagents at the sys.modules level so the module loads
cleanly in any environment.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers to load agent.py with mocked NAT + deepagents
# ---------------------------------------------------------------------------


def _load_agent_module():
    """Import agent.agent with NAT and deepagents fully mocked.

    Returns (module, mock_create_deep_agent, mock_model).
    """
    import importlib
    import sys

    mock_model = MagicMock(name="llm_model")
    mock_agent = MagicMock(name="compiled_graph")

    mock_sync_builder = MagicMock()
    mock_sync_builder.current.return_value.get_llm.return_value = mock_model

    mock_create_deep_agent = MagicMock(return_value=mock_agent)

    nat_mocks = {
        "nat": MagicMock(),
        "nat.builder": MagicMock(),
        "nat.builder.framework_enum": MagicMock(LLMFrameworkEnum=MagicMock(LANGCHAIN="langchain")),
        "nat.builder.sync_builder": MagicMock(SyncBuilder=mock_sync_builder),
        "deepagents": MagicMock(create_deep_agent=mock_create_deep_agent),
    }

    # Remove cached module so it re-executes module-level code
    sys.modules.pop("hermes_computer_use.agent.agent", None)

    with patch.dict(sys.modules, nat_mocks):
        mod = importlib.import_module("hermes_computer_use.agent.agent")

    return mod, mock_create_deep_agent, mock_model


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAgentModuleLoads:
    def test_module_imports_without_real_nat(self):
        """agent.py must load without real NAT or deepagents installed."""
        mod, _, _ = _load_agent_module()
        assert mod is not None

    def test_agent_attribute_exists(self):
        """Module must expose an 'agent' attribute (the CompiledStateGraph)."""
        mod, _, _ = _load_agent_module()
        assert hasattr(mod, "agent")
        assert mod.agent is not None

    def test_system_prompt_attribute_exists(self):
        """Module must expose a SYSTEM_PROMPT string constant."""
        mod, _, _ = _load_agent_module()
        assert hasattr(mod, "SYSTEM_PROMPT")
        assert isinstance(mod.SYSTEM_PROMPT, str)
        assert len(mod.SYSTEM_PROMPT) > 0


class TestSyncBuilderIntegration:
    def test_get_llm_called_with_agent_key(self):
        """SyncBuilder.current().get_llm() must be called with 'agent'."""
        import importlib
        import sys

        mock_sync_builder = MagicMock()
        mock_get_llm = mock_sync_builder.current.return_value.get_llm

        nat_mocks = {
            "nat": MagicMock(),
            "nat.builder": MagicMock(),
            "nat.builder.framework_enum": MagicMock(LLMFrameworkEnum=MagicMock(LANGCHAIN="langchain")),
            "nat.builder.sync_builder": MagicMock(SyncBuilder=mock_sync_builder),
            "deepagents": MagicMock(create_deep_agent=MagicMock(return_value=MagicMock())),
        }

        sys.modules.pop("hermes_computer_use.agent.agent", None)
        with patch.dict(sys.modules, nat_mocks):
            importlib.import_module("hermes_computer_use.agent.agent")

        mock_get_llm.assert_called_once()
        call_args = mock_get_llm.call_args
        assert call_args[0][0] == "agent"

    def test_get_llm_called_with_langchain_wrapper(self):
        """get_llm() must request wrapper_type=LLMFrameworkEnum.LANGCHAIN."""
        import importlib
        import sys

        mock_framework = MagicMock()
        mock_framework.LANGCHAIN = "langchain_sentinel"
        mock_sync_builder = MagicMock()
        mock_get_llm = mock_sync_builder.current.return_value.get_llm

        nat_mocks = {
            "nat": MagicMock(),
            "nat.builder": MagicMock(),
            "nat.builder.framework_enum": MagicMock(LLMFrameworkEnum=mock_framework),
            "nat.builder.sync_builder": MagicMock(SyncBuilder=mock_sync_builder),
            "deepagents": MagicMock(create_deep_agent=MagicMock(return_value=MagicMock())),
        }

        sys.modules.pop("hermes_computer_use.agent.agent", None)
        with patch.dict(sys.modules, nat_mocks):
            importlib.import_module("hermes_computer_use.agent.agent")

        call_kwargs = mock_get_llm.call_args[1]
        assert call_kwargs.get("wrapper_type") == "langchain_sentinel"


class TestCreateDeepAgentCall:
    def test_create_deep_agent_called(self):
        """create_deep_agent() must be called exactly once at module load."""
        mod, mock_cda, _ = _load_agent_module()
        mock_cda.assert_called_once()

    def test_model_passed_to_create_deep_agent(self):
        """The model from SyncBuilder must be forwarded to create_deep_agent."""
        mod, mock_cda, mock_model = _load_agent_module()
        call_kwargs = mock_cda.call_args[1]
        assert call_kwargs["model"] is mock_model

    def test_tools_passed_to_create_deep_agent(self):
        """create_deep_agent must receive a non-empty tools list."""
        mod, mock_cda, _ = _load_agent_module()
        call_kwargs = mock_cda.call_args[1]
        assert "tools" in call_kwargs
        assert len(call_kwargs["tools"]) > 0

    def test_system_prompt_passed_to_create_deep_agent(self):
        """create_deep_agent must receive the SYSTEM_PROMPT string."""
        mod, mock_cda, _ = _load_agent_module()
        call_kwargs = mock_cda.call_args[1]
        assert "system_prompt" in call_kwargs
        assert isinstance(call_kwargs["system_prompt"], str)
        assert len(call_kwargs["system_prompt"]) > 0

    def test_system_prompt_mentions_screenshot(self):
        """SYSTEM_PROMPT should mention screenshot as the first step."""
        mod, _, _ = _load_agent_module()
        assert "screenshot" in mod.SYSTEM_PROMPT.lower()

    def test_all_11_tools_passed(self):
        """All 11 computer-use tools must be forwarded to create_deep_agent."""
        mod, mock_cda, _ = _load_agent_module()
        call_kwargs = mock_cda.call_args[1]
        assert len(call_kwargs["tools"]) == 11
