"""Tests for action executor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from hermes_computer_use.tools.actions import ActionResult, DesktopActionExecutor


class TestDesktopActionExecutor:
    """Tests for the DesktopActionExecutor class."""

    def test_create_with_no_simulator(self):
        """Test creating executor without simulator creates one."""
        with patch("hermes_computer_use.tools.actions.InputSimulator") as mock:
            mock.return_value = MagicMock()
            executor = DesktopActionExecutor()
            assert executor.input_simulator is not None

    def test_create_with_simulator(self, mock_input_simulator):
        """Test creating executor with provided simulator."""
        executor = DesktopActionExecutor(input_simulator=mock_input_simulator)
        assert executor.input_simulator is mock_input_simulator

    def test_unknown_action(self):
        """Test handling unknown action."""
        executor = DesktopActionExecutor()
        result = executor.execute("nonexistent_action")

        assert isinstance(result, ActionResult)
        assert result.success is False
        assert "Unknown action" in result.error

    @patch("hermes_computer_use.tools.actions.InputSimulator")
    def test_execute_click(self, mock_sim_class):
        """Test execute click action."""
        mock_sim = MagicMock()
        mock_sim.click.return_value = {"action": "click", "status": "success"}
        mock_sim_class.return_value = mock_sim

        executor = DesktopActionExecutor(input_simulator=mock_sim)
        result = executor.execute("click", x=100, y=200, button="left")

        assert result.success is True
        assert result.action == "click"
        mock_sim.click.assert_called_once()

    @patch("hermes_computer_use.tools.actions.InputSimulator")
    def test_execute_type(self, mock_sim_class):
        """Test execute type action."""
        mock_sim = MagicMock()
        mock_sim.type_text.return_value = {"action": "type", "status": "success"}
        mock_sim_class.return_value = mock_sim

        executor = DesktopActionExecutor(input_simulator=mock_sim)
        result = executor.execute("type", text="Hello")

        assert result.success is True
        assert result.action == "type"
        mock_sim.type_text.assert_called_once_with("Hello", interval=0.05)

    @patch("hermes_computer_use.tools.actions.InputSimulator")
    def test_execute_key(self, mock_sim_class):
        """Test execute key action."""
        mock_sim = MagicMock()
        mock_sim.press_key.return_value = {"action": "press", "status": "success"}
        mock_sim_class.return_value = mock_sim

        executor = DesktopActionExecutor(input_simulator=mock_sim)
        result = executor.execute("key", key="enter")

        assert result.success is True
        assert result.action == "key"
        mock_sim.press_key.assert_called_once_with("enter")

    @patch("hermes_computer_use.tools.actions.InputSimulator")
    def test_execute_key_with_combo(self, mock_sim_class):
        """Test execute key with combination."""
        mock_sim = MagicMock()
        mock_sim.key_combo.return_value = {"action": "combo", "status": "success"}
        mock_sim_class.return_value = mock_sim

        executor = DesktopActionExecutor(input_simulator=mock_sim)
        result = executor.execute("key", key="c", combo=["ctrl"])

        assert result.success is True
        assert result.action == "key"
        mock_sim.key_combo.assert_called_once_with(["ctrl", "c"])

    @patch("hermes_computer_use.tools.actions.subprocess.Popen")
    def test_execute_open_app(self, mock_popen):
        """Test execute open_app action."""
        executor = DesktopActionExecutor()
        result = executor.execute("open_app", app_name="firefox")

        assert result.success is True
        assert result.action == "open_app"
        assert result.result["app"] == "firefox"
        mock_popen.assert_called_once()

    @patch("hermes_computer_use.tools.actions.subprocess.Popen")
    def test_execute_open_app_with_args(self, mock_popen):
        """Test open app with arguments."""
        executor = DesktopActionExecutor()
        result = executor.execute("open_app", app_name="code", args=["--new-window"])

        assert result.success is True
        mock_popen.assert_called_once_with(
            ["code", "--new-window"],
            stdout=-3,
            stderr=-3,
        )

    @patch("hermes_computer_use.tools.actions.subprocess.Popen")
    def test_execute_open_app_error(self, mock_popen):
        """Test open app on error."""
        mock_popen.side_effect = FileNotFoundError("app not found")

        executor = DesktopActionExecutor()
        result = executor.execute("open_app", app_name="nonexistent_app_12345")

        assert result.success is True  # Still success, but with error in result
        assert result.result["status"] == "error"

    @patch("hermes_computer_use.tools.actions.subprocess.Popen")
    def test_execute_navigate(self, mock_popen):
        """Test execute navigate action."""
        executor = DesktopActionExecutor()
        result = executor.execute("navigate", url="https://example.com")

        assert result.success is True
        assert result.action == "navigate"
        assert result.result["url"] == "https://example.com"
        mock_popen.assert_called_once_with(
            ["xdg-open", "https://example.com"],
            stdout=-3,
            stderr=-3,
        )

    @patch("hermes_computer_use.tools.actions.time.sleep")
    def test_execute_wait(self, mock_sleep):
        """Test execute wait action."""
        executor = DesktopActionExecutor()
        result = executor.execute("wait", seconds=2.5)

        assert result.success is True
        assert result.action == "wait"
        assert result.result["duration"] == 2.5
        mock_sleep.assert_called_once_with(2.5)

    @patch("hermes_computer_use.tools.actions.InputSimulator")
    @patch("hermes_computer_use.tools.actions.time.sleep")
    def test_execute_search(self, mock_sleep, mock_sim_class):
        """Test execute search action."""
        mock_sim = MagicMock()
        mock_sim.press_key.return_value = {"action": "press", "status": "success"}
        mock_sim.type_text.return_value = {"action": "type", "status": "success"}
        mock_sim_class.return_value = mock_sim

        executor = DesktopActionExecutor(input_simulator=mock_sim)
        result = executor.execute("search", text="Calculator")

        assert result.success is True
        assert result.action == "search"
        assert result.result["query"] == "Calculator"

    @patch("hermes_computer_use.tools.actions.subprocess.Popen")
    def test_execute_navigate_error(self, mock_popen):
        """Test navigate on error."""
        mock_popen.side_effect = FileNotFoundError("xdg-open not found")

        executor = DesktopActionExecutor()
        result = executor.execute("navigate", url="https://example.com")

        assert result.success is True
        assert result.result["status"] == "error"


class TestActionSequence:
    """Tests for action sequence execution."""

    @patch("hermes_computer_use.tools.actions.InputSimulator")
    def test_sequence_success(self, mock_sim_class):
        """Test successful action sequence."""
        mock_sim = MagicMock()
        mock_sim.press_key.return_value = {"action": "press", "status": "success"}
        mock_sim.type_text.return_value = {"action": "type", "status": "success"}
        mock_sim_class.return_value = mock_sim

        executor = DesktopActionExecutor(input_simulator=mock_sim)
        actions = [
            {"action": "key", "params": {"key": "enter"}},
            {"action": "type", "params": {"text": "hello"}},
        ]

        results = executor.execute_sequence(actions)

        assert len(results) == 2
        assert all(r.success for r in results)

    @patch("hermes_computer_use.tools.actions.InputSimulator")
    def test_sequence_failure_stops(self, mock_sim_class):
        """Test that sequence stops on first failure."""
        mock_sim = MagicMock()
        mock_sim.press_key.side_effect = Exception("Simulated error")
        mock_sim_class.return_value = mock_sim

        executor = DesktopActionExecutor(input_simulator=mock_sim)
        actions = [
            {"action": "key", "params": {"key": "enter"}},
            {"action": "type", "params": {"text": "hello"}},
            {"action": "wait", "params": {"seconds": 1}},
        ]

        results = executor.execute_sequence(actions)

        assert len(results) == 1  # Only first action executed
        assert results[0].success is False

    def test_empty_sequence(self):
        """Test empty action list."""
        executor = DesktopActionExecutor()
        results = executor.execute_sequence([])

        assert len(results) == 0

    @patch("hermes_computer_use.tools.actions.InputSimulator")
    def test_sequence_missing_action(self, mock_sim_class):
        """Test sequence with missing action key."""
        mock_sim = MagicMock()
        mock_sim_class.return_value = mock_sim

        executor = DesktopActionExecutor(input_simulator=mock_sim)
        actions = [
            {"params": {"text": "hello"}},  # Missing 'action' key
        ]

        results = executor.execute_sequence(actions)
        assert results[0].success is False  # Unknown action
