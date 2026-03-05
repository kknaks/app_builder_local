"""Claude Code CLI pty spawn module.

Spawns Claude Code CLI as a child process using pty for real-time output streaming.
Handles timeout (10 min), graceful shutdown (SIGTERM→SIGKILL), zombie cleanup.
"""

import asyncio
import logging
import os
import pty
import re
import signal
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ANSI escape code pattern (colors, cursor movement, etc.)
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|\x1b\].*?\x07|\x1b\[[\?]?[0-9;]*[hl]")

# Token usage pattern from Claude Code stdout
# Example: "Total tokens: 1234 input, 5678 output"
# Or: "input_tokens: 1234, output_tokens: 5678"
_TOKEN_PATTERN = re.compile(
    r"(?:Total\s+)?(?:tokens?:?\s*)?(\d[\d,]*)\s*input.*?(\d[\d,]*)\s*output",
    re.IGNORECASE,
)

# Alternative token pattern: "Cost: $0.0123 (1234 input + 5678 output tokens)"
_TOKEN_PATTERN_ALT = re.compile(
    r"(\d[\d,]*)\s*input\s*\+?\s*(\d[\d,]*)\s*output\s*tokens?",
    re.IGNORECASE,
)

# Cost pattern: "Cost: $X.XXXX" or "Total cost: $X.XXXX"
_COST_PATTERN = re.compile(r"(?:Total\s+)?[Cc]ost:\s*\$?([\d.]+)", re.IGNORECASE)

DEFAULT_TIMEOUT = 600  # 10 minutes
KILL_GRACE_PERIOD = 5  # seconds before SIGKILL after SIGTERM


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    return _ANSI_RE.sub("", text)


def parse_token_usage(text: str) -> dict | None:
    """Parse token usage from Claude Code stdout line.

    Returns dict with input_tokens, output_tokens, and optional cost_usd,
    or None if no token info found.
    """
    # Try primary pattern
    match = _TOKEN_PATTERN.search(text)
    if not match:
        match = _TOKEN_PATTERN_ALT.search(text)

    if match:
        result = {
            "input_tokens": int(match.group(1).replace(",", "")),
            "output_tokens": int(match.group(2).replace(",", "")),
        }
        # Try to find cost
        cost_match = _COST_PATTERN.search(text)
        if cost_match:
            result["cost_usd"] = float(cost_match.group(1))
        return result

    return None


@dataclass
class AgentProcess:
    """Represents a running agent process."""

    pid: int
    project_id: int
    agent: str
    task_id: int | None = None
    _process_fd: int | None = field(default=None, repr=False)

    def is_alive(self) -> bool:
        """Check if the process is still running."""
        try:
            os.kill(self.pid, 0)
            return True
        except OSError:
            return False

    async def terminate(self) -> bool:
        """Graceful shutdown: SIGTERM → wait → SIGKILL.

        Returns True if process was terminated, False if already dead.
        """
        if not self.is_alive():
            return False

        try:
            os.kill(self.pid, signal.SIGTERM)
            logger.info("Sent SIGTERM to pid %d (agent=%s, task=%s)", self.pid, self.agent, self.task_id)
        except OSError:
            return False

        # Wait for graceful shutdown
        for _ in range(KILL_GRACE_PERIOD * 10):  # Check every 100ms
            await asyncio.sleep(0.1)
            if not self.is_alive():
                logger.info("Process %d terminated gracefully", self.pid)
                self._cleanup()
                return True

        # Force kill
        try:
            os.kill(self.pid, signal.SIGKILL)
            logger.warning("Sent SIGKILL to pid %d after grace period", self.pid)
        except OSError:
            pass

        # Wait for SIGKILL to take effect
        await asyncio.sleep(0.5)
        self._cleanup()
        return True

    def _cleanup(self) -> None:
        """Clean up file descriptor and reap zombie."""
        if self._process_fd is not None:
            try:
                os.close(self._process_fd)
            except OSError:
                pass
            self._process_fd = None

        # Reap zombie process
        try:
            os.waitpid(self.pid, os.WNOHANG)
        except ChildProcessError:
            pass


class AgentProcessManager:
    """Manages running agent processes.

    Singleton-like manager that tracks all running agent processes
    and provides spawn/terminate/cleanup operations.
    """

    def __init__(self) -> None:
        self._processes: dict[int, AgentProcess] = {}  # task_id -> AgentProcess
        self._lock = asyncio.Lock()

    @property
    def running_count(self) -> int:
        """Number of currently running processes."""
        return len(self._processes)

    def get_process(self, task_id: int) -> AgentProcess | None:
        """Get a running process by task ID."""
        return self._processes.get(task_id)

    def get_processes_for_project(self, project_id: int) -> list[AgentProcess]:
        """Get all running processes for a project."""
        return [p for p in self._processes.values() if p.project_id == project_id]

    async def spawn_agent(
        self,
        agent_md_path: str,
        prompt: str,
        project_dir: str,
        project_id: int,
        agent: str,
        task_id: int,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> AsyncGenerator[str, None]:
        """Spawn a Claude Code CLI process and stream output lines.

        Args:
            agent_md_path: Path to agent .md file
            prompt: The prompt to send to Claude Code
            project_dir: Working directory for the agent
            project_id: Project ID for tracking
            agent: Agent name (e.g., "pm", "backend")
            task_id: Task ID for tracking
            timeout: Timeout in seconds (default 10 min)

        Yields:
            str: Lines of output from the process (ANSI stripped)

        Raises:
            TimeoutError: If process exceeds timeout
            RuntimeError: If spawn fails
        """
        # Build command
        cmd = [
            "claude",
            "--dangerously-skip-permissions",
            "-p",
            prompt,
        ]

        if agent_md_path:
            cmd.extend(["--agent-file", agent_md_path])

        # Spawn with pty
        master_fd, slave_fd = pty.openpty()

        try:
            pid = os.fork()
        except OSError as e:
            os.close(master_fd)
            os.close(slave_fd)
            raise RuntimeError(f"Failed to fork: {e}") from e

        if pid == 0:
            # Child process
            os.close(master_fd)
            os.setsid()

            # Redirect stdio to pty
            os.dup2(slave_fd, 0)
            os.dup2(slave_fd, 1)
            os.dup2(slave_fd, 2)
            if slave_fd > 2:
                os.close(slave_fd)

            os.chdir(project_dir)
            os.execvp(cmd[0], cmd)
            os._exit(1)  # Only reached if exec fails

        # Parent process
        os.close(slave_fd)

        process = AgentProcess(
            pid=pid,
            project_id=project_id,
            agent=agent,
            task_id=task_id,
            _process_fd=master_fd,
        )

        async with self._lock:
            self._processes[task_id] = process

        logger.info("Spawned agent process pid=%d agent=%s task=%d", pid, agent, task_id)

        try:
            async for line in self._read_output(master_fd, pid, timeout):
                yield line
        finally:
            # Cleanup
            process._cleanup()
            async with self._lock:
                self._processes.pop(task_id, None)

            # Reap zombie
            try:
                os.waitpid(pid, os.WNOHANG)
            except ChildProcessError:
                pass

    async def _read_output(
        self,
        fd: int,
        pid: int,
        timeout: int,
    ) -> AsyncGenerator[str, None]:
        """Read output from pty fd asynchronously with timeout."""
        loop = asyncio.get_event_loop()
        buffer = ""
        deadline = loop.time() + timeout

        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                # Timeout reached
                try:
                    os.kill(pid, signal.SIGTERM)
                    await asyncio.sleep(KILL_GRACE_PERIOD)
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except OSError:
                        pass
                except OSError:
                    pass
                raise TimeoutError(f"Agent process {pid} timed out after {timeout}s")

            try:
                # Read with timeout using asyncio
                data = await asyncio.wait_for(
                    loop.run_in_executor(None, os.read, fd, 4096),
                    timeout=min(remaining, 5.0),
                )
            except asyncio.TimeoutError:
                # Check if process is still alive
                try:
                    result = os.waitpid(pid, os.WNOHANG)
                    if result[0] != 0:
                        # Process ended
                        break
                except ChildProcessError:
                    break
                continue
            except OSError:
                # fd closed or process ended
                break

            if not data:
                break

            text = data.decode("utf-8", errors="replace")
            buffer += text

            # Yield complete lines
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                cleaned = strip_ansi(line).strip()
                if cleaned:
                    yield cleaned

            # Also yield lines terminated by \r (for progress updates)
            while "\r" in buffer:
                line, buffer = buffer.split("\r", 1)
                cleaned = strip_ansi(line).strip()
                if cleaned:
                    yield cleaned

        # Yield remaining buffer
        if buffer:
            cleaned = strip_ansi(buffer).strip()
            if cleaned:
                yield cleaned

    async def cancel_task(self, task_id: int) -> bool:
        """Cancel a running task by terminating its process.

        Returns True if process was found and terminated.
        """
        process = self._processes.get(task_id)
        if not process:
            return False

        result = await process.terminate()

        async with self._lock:
            self._processes.pop(task_id, None)

        return result

    async def cancel_project(self, project_id: int) -> int:
        """Cancel all running tasks for a project.

        Returns number of processes cancelled.
        """
        processes = self.get_processes_for_project(project_id)
        count = 0
        for proc in processes:
            if await proc.terminate():
                count += 1
            if proc.task_id is not None:
                async with self._lock:
                    self._processes.pop(proc.task_id, None)
        return count

    async def cleanup_all(self) -> int:
        """Terminate all running processes (for shutdown).

        Returns number of processes cleaned up.
        """
        count = 0
        async with self._lock:
            for task_id, proc in list(self._processes.items()):
                if await proc.terminate():
                    count += 1
            self._processes.clear()
        return count


# Global process manager instance
process_manager = AgentProcessManager()
