"""Tests for agent_runner module — strip_ansi, parse_token_usage, AgentProcessManager."""

import pytest

from app.core.agent_runner import (
    AgentProcess,
    AgentProcessManager,
    parse_token_usage,
    strip_ansi,
)


class TestStripAnsi:
    """Tests for ANSI escape code removal."""

    def test_no_ansi(self):
        assert strip_ansi("hello world") == "hello world"

    def test_color_codes(self):
        assert strip_ansi("\x1b[31mred text\x1b[0m") == "red text"

    def test_bold(self):
        assert strip_ansi("\x1b[1mbold\x1b[0m normal") == "bold normal"

    def test_cursor_movement(self):
        assert strip_ansi("\x1b[2Ahello") == "hello"

    def test_complex_sequence(self):
        text = "\x1b[38;5;196mcolored\x1b[0m \x1b[1;32mgreen bold\x1b[0m"
        assert strip_ansi(text) == "colored green bold"

    def test_empty_string(self):
        assert strip_ansi("") == ""

    def test_osc_sequences(self):
        # OSC title set: \x1b]0;Title\x07
        assert strip_ansi("\x1b]0;Terminal Title\x07hello") == "hello"

    def test_private_mode(self):
        # e.g. \x1b[?25h (show cursor)
        assert strip_ansi("\x1b[?25hvisible") == "visible"


class TestParseTokenUsage:
    """Tests for token usage parsing from CLI output."""

    def test_standard_format(self):
        line = "Total tokens: 1,234 input, 5,678 output"
        result = parse_token_usage(line)
        assert result is not None
        assert result["input_tokens"] == 1234
        assert result["output_tokens"] == 5678

    def test_with_cost(self):
        line = "Total cost: $0.0456 (1234 input + 5678 output tokens)"
        result = parse_token_usage(line)
        assert result is not None
        assert result["input_tokens"] == 1234
        assert result["output_tokens"] == 5678
        assert result["cost_usd"] == 0.0456

    def test_simple_format(self):
        line = "tokens: 500 input, 200 output"
        result = parse_token_usage(line)
        assert result is not None
        assert result["input_tokens"] == 500
        assert result["output_tokens"] == 200

    def test_no_match(self):
        assert parse_token_usage("hello world") is None
        assert parse_token_usage("processing...") is None

    def test_empty_string(self):
        assert parse_token_usage("") is None


class TestAgentProcess:
    """Tests for AgentProcess dataclass."""

    def test_creation(self):
        proc = AgentProcess(pid=99999, project_id=1, agent="pm", task_id=1)
        assert proc.pid == 99999
        assert proc.project_id == 1
        assert proc.agent == "pm"
        assert proc.task_id == 1

    def test_is_alive_dead_process(self):
        # Use a PID that almost certainly doesn't exist
        proc = AgentProcess(pid=999999, project_id=1, agent="pm")
        assert proc.is_alive() is False


class TestAgentProcessManager:
    """Tests for AgentProcessManager."""

    def test_initial_state(self):
        mgr = AgentProcessManager()
        assert mgr.running_count == 0

    def test_get_process_empty(self):
        mgr = AgentProcessManager()
        assert mgr.get_process(999) is None

    def test_get_processes_for_project_empty(self):
        mgr = AgentProcessManager()
        assert mgr.get_processes_for_project(1) == []

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_task(self):
        mgr = AgentProcessManager()
        result = await mgr.cancel_task(999)
        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_project(self):
        mgr = AgentProcessManager()
        result = await mgr.cancel_project(999)
        assert result == 0

    @pytest.mark.asyncio
    async def test_cleanup_all_empty(self):
        mgr = AgentProcessManager()
        result = await mgr.cleanup_all()
        assert result == 0

    @pytest.mark.asyncio
    async def test_terminate_dead_process(self):
        proc = AgentProcess(pid=999999, project_id=1, agent="pm")
        result = await proc.terminate()
        assert result is False
