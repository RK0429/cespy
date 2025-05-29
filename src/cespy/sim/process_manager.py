#!/usr/bin/env python
# coding=utf-8
"""Process manager for handling simulation subprocess execution.

This module provides a manager for executing and monitoring simulation processes,
with support for timeouts, resource limits, and process cleanup.
"""

import logging
import os
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    psutil = None
    HAS_PSUTIL = False

from ..core import constants as core_constants

_logger = logging.getLogger("cespy.ProcessManager")


@dataclass
class ProcessInfo:
    """Information about a running process."""

    pid: int
    command: List[str]
    start_time: float
    working_directory: Path
    stdout_file: Optional[Path] = None
    stderr_file: Optional[Path] = None
    process: Optional[subprocess.Popen] = None
    psutil_process: Optional[Any] = None  # psutil.Process if available


@dataclass
class ProcessResult:
    """Result of a process execution."""

    return_code: int
    stdout_path: Optional[Path]
    stderr_path: Optional[Path]
    duration: float
    terminated: bool = False
    error_message: Optional[str] = None


class ProcessManager:
    """Manages subprocess execution for simulations.

    This class handles:
    - Process launching with proper resource management
    - Timeout enforcement
    - Process monitoring and cleanup
    - Zombie process prevention
    - Resource usage tracking
    """

    def __init__(self, max_processes: int = 4, cleanup_interval: float = 60.0):
        """Initialize process manager.

        Args:
            max_processes: Maximum number of concurrent processes
            cleanup_interval: Interval for cleaning up zombie processes (seconds)
        """
        self.max_processes = max_processes
        self.cleanup_interval = cleanup_interval

        # Process tracking
        self._processes: Dict[int, ProcessInfo] = {}
        self._lock = threading.Lock()
        self._process_counter = 0

        # Resource monitoring
        self._cpu_percent_history: List[float] = []
        self._memory_usage_history: List[float] = []

        # Cleanup thread
        self._cleanup_thread = None
        self._stop_cleanup = threading.Event()
        self._start_cleanup_thread()

        _logger.info("ProcessManager initialized with max_processes=%d", max_processes)

    def execute(
        self,
        command: List[str],
        working_directory: Path,
        timeout: Optional[float] = None,
        env: Optional[Dict[str, str]] = None,
        stdout_file: Optional[Path] = None,
        stderr_file: Optional[Path] = None,
        priority: Optional[int] = None,
    ) -> Tuple[int, ProcessResult]:
        """Execute a command as a subprocess.

        Args:
            command: Command and arguments to execute
            working_directory: Working directory for the process
            timeout: Maximum execution time in seconds
            env: Environment variables for the process
            stdout_file: File to redirect stdout (None for pipe)
            stderr_file: File to redirect stderr (None for pipe)
            priority: Process priority (nice value on Unix, priority class on Windows)

        Returns:
            Tuple of (process_id, ProcessResult)

        Raises:
            RuntimeError: If process limit is reached
            OSError: If process cannot be started
        """
        with self._lock:
            if len(self._processes) >= self.max_processes:
                raise RuntimeError(f"Process limit ({self.max_processes}) reached")

            process_id = self._process_counter
            self._process_counter += 1

        # Prepare process environment
        process_env = os.environ.copy()
        if env:
            process_env.update(env)

        # Prepare stdout/stderr
        stdout_handle = None
        stderr_handle = None

        try:
            if stdout_file:
                stdout_handle = open(stdout_file, "w", encoding="utf-8")
            else:
                stdout_handle = subprocess.PIPE

            if stderr_file:
                stderr_handle = open(stderr_file, "w", encoding="utf-8")
            else:
                stderr_handle = subprocess.PIPE

            # Start process
            start_time = time.time()

            _logger.debug(
                "Starting process: %s in %s", " ".join(command), working_directory
            )

            process = subprocess.Popen(
                command,
                cwd=str(working_directory),
                env=process_env,
                stdout=stdout_handle,
                stderr=stderr_handle,
                # Prevent console window on Windows
                creationflags=subprocess.CREATE_NO_WINDOW
                if sys.platform == "win32"
                else 0,
            )

            # Create process info
            process_info = ProcessInfo(
                pid=process.pid,
                command=command,
                start_time=start_time,
                working_directory=working_directory,
                stdout_file=stdout_file,
                stderr_file=stderr_file,
                process=process,
            )

            # Set process priority if requested
            if priority is not None:
                self._set_process_priority(process.pid, priority)

            # Track with psutil if available
            if HAS_PSUTIL:
                try:
                    process_info.psutil_process = psutil.Process(process.pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            # Store process info
            with self._lock:
                self._processes[process_id] = process_info

            # Wait for completion with timeout
            try:
                return_code = process.wait(timeout=timeout)
                terminated = False
                error_message = None
            except subprocess.TimeoutExpired:
                _logger.warning(
                    "Process %d timed out after %s seconds", process_id, timeout
                )
                self._terminate_process(process_info)
                return_code = -1
                terminated = True
                error_message = f"Process timed out after {timeout} seconds"
            except Exception as e:
                _logger.error("Error waiting for process %d: %s", process_id, e)
                self._terminate_process(process_info)
                return_code = -1
                terminated = True
                error_message = str(e)

            # Calculate duration
            duration = time.time() - start_time

            # Create result
            result = ProcessResult(
                return_code=return_code,
                stdout_path=stdout_file,
                stderr_path=stderr_file,
                duration=duration,
                terminated=terminated,
                error_message=error_message,
            )

            # Clean up
            with self._lock:
                del self._processes[process_id]

            _logger.debug(
                "Process %d completed with code %d in %.2f seconds",
                process_id,
                return_code,
                duration,
            )

            return process_id, result

        finally:
            # Close file handles if we opened them
            if stdout_handle and stdout_file:
                stdout_handle.close()
            if stderr_handle and stderr_file:
                stderr_handle.close()

    def terminate_process(self, process_id: int) -> bool:
        """Terminate a running process.

        Args:
            process_id: ID of the process to terminate

        Returns:
            True if process was terminated, False if not found
        """
        with self._lock:
            if process_id not in self._processes:
                return False

            process_info = self._processes[process_id]

        self._terminate_process(process_info)

        with self._lock:
            del self._processes[process_id]

        return True

    def get_active_processes(self) -> Dict[int, Dict[str, Any]]:
        """Get information about active processes.

        Returns:
            Dictionary mapping process IDs to process information
        """
        with self._lock:
            result = {}
            for pid, info in self._processes.items():
                result[pid] = {
                    "pid": info.pid,
                    "command": " ".join(info.command),
                    "duration": time.time() - info.start_time,
                    "working_directory": str(info.working_directory),
                }

                # Add resource usage if available
                if HAS_PSUTIL and info.psutil_process:
                    try:
                        result[pid]["cpu_percent"] = info.psutil_process.cpu_percent()
                        result[pid]["memory_mb"] = (
                            info.psutil_process.memory_info().rss / 1024 / 1024
                        )
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

            return result

    def get_resource_usage(self) -> Dict[str, float]:
        """Get current resource usage statistics.

        Returns:
            Dictionary with resource usage metrics
        """
        total_cpu = 0.0
        total_memory_mb = 0.0
        process_count = 0

        with self._lock:
            for info in self._processes.values():
                if HAS_PSUTIL and info.psutil_process:
                    try:
                        total_cpu += info.psutil_process.cpu_percent()
                        total_memory_mb += (
                            info.psutil_process.memory_info().rss / 1024 / 1024
                        )
                        process_count += 1
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

        return {
            "process_count": process_count,
            "total_cpu_percent": total_cpu,
            "total_memory_mb": total_memory_mb,
            "avg_cpu_percent": total_cpu / process_count if process_count > 0 else 0.0,
            "avg_memory_mb": total_memory_mb / process_count
            if process_count > 0
            else 0.0,
        }

    def cleanup_zombies(self) -> int:
        """Clean up zombie processes.

        Returns:
            Number of zombie processes cleaned up
        """
        if not HAS_PSUTIL:
            return 0

        cleaned = 0

        # Find zombie processes matching our simulator patterns
        for proc in psutil.process_iter(["pid", "name", "status"]):
            try:
                if proc.info["status"] == psutil.STATUS_ZOMBIE:
                    # Check if it's one of our simulators
                    if any(
                        sim in proc.info["name"].lower()
                        for sim in ["ltspice", "ngspice", "qspice", "xyce"]
                    ):
                        _logger.info(
                            "Cleaning up zombie process %d (%s)",
                            proc.info["pid"],
                            proc.info["name"],
                        )
                        proc.kill()
                        cleaned += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        return cleaned

    def shutdown(self, timeout: float = 10.0) -> None:
        """Shutdown the process manager.

        Args:
            timeout: Maximum time to wait for processes to terminate
        """
        _logger.info("Shutting down ProcessManager")

        # Stop cleanup thread
        self._stop_cleanup_thread()

        # Terminate all running processes
        with self._lock:
            processes_to_terminate = list(self._processes.values())

        for process_info in processes_to_terminate:
            self._terminate_process(process_info)

        # Wait for processes to terminate
        start_time = time.time()
        while time.time() - start_time < timeout:
            with self._lock:
                if not self._processes:
                    break
            time.sleep(0.1)

        # Force kill any remaining processes
        with self._lock:
            for process_info in self._processes.values():
                self._kill_process(process_info)
            self._processes.clear()

    def _set_process_priority(self, pid: int, priority: int) -> None:
        """Set process priority.

        Args:
            pid: Process ID
            priority: Priority value (platform-specific)
        """
        if HAS_PSUTIL:
            try:
                proc = psutil.Process(pid)
                if sys.platform == "win32":
                    # Windows priority classes
                    priority_class = {
                        -2: psutil.IDLE_PRIORITY_CLASS,
                        -1: psutil.BELOW_NORMAL_PRIORITY_CLASS,
                        0: psutil.NORMAL_PRIORITY_CLASS,
                        1: psutil.ABOVE_NORMAL_PRIORITY_CLASS,
                        2: psutil.HIGH_PRIORITY_CLASS,
                    }.get(priority, psutil.NORMAL_PRIORITY_CLASS)
                    proc.nice(priority_class)
                else:
                    # Unix nice values (-20 to 19)
                    proc.nice(priority)
            except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
                pass

    def _terminate_process(self, process_info: ProcessInfo) -> None:
        """Terminate a process gracefully.

        Args:
            process_info: Process to terminate
        """
        if process_info.process and process_info.process.poll() is None:
            try:
                process_info.process.terminate()
                # Give it a chance to terminate gracefully
                process_info.process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                # Force kill if necessary
                self._kill_process(process_info)
            except Exception as e:
                _logger.error("Error terminating process %d: %s", process_info.pid, e)

    def _kill_process(self, process_info: ProcessInfo) -> None:
        """Force kill a process.

        Args:
            process_info: Process to kill
        """
        if process_info.process and process_info.process.poll() is None:
            try:
                if sys.platform == "win32":
                    process_info.process.kill()
                else:
                    os.kill(process_info.pid, signal.SIGKILL)
            except Exception as e:
                _logger.error("Error killing process %d: %s", process_info.pid, e)

    def _cleanup_thread_func(self) -> None:
        """Background thread for cleaning up zombie processes."""
        while not self._stop_cleanup.is_set():
            try:
                # Clean up zombies periodically
                cleaned = self.cleanup_zombies()
                if cleaned > 0:
                    _logger.info("Cleaned up %d zombie processes", cleaned)

                # Update resource tracking
                usage = self.get_resource_usage()
                if usage["process_count"] > 0:
                    self._cpu_percent_history.append(usage["total_cpu_percent"])
                    self._memory_usage_history.append(usage["total_memory_mb"])

                    # Keep only recent history
                    max_history = 100
                    if len(self._cpu_percent_history) > max_history:
                        self._cpu_percent_history = self._cpu_percent_history[
                            -max_history:
                        ]
                    if len(self._memory_usage_history) > max_history:
                        self._memory_usage_history = self._memory_usage_history[
                            -max_history:
                        ]

            except Exception as e:
                _logger.error("Error in cleanup thread: %s", e)

            # Wait for next cleanup or stop signal
            self._stop_cleanup.wait(self.cleanup_interval)

    def _start_cleanup_thread(self) -> None:
        """Start the cleanup thread."""
        if HAS_PSUTIL:
            self._cleanup_thread = threading.Thread(
                target=self._cleanup_thread_func,
                daemon=True,
                name="ProcessManager-Cleanup",
            )
            self._cleanup_thread.start()

    def _stop_cleanup_thread(self) -> None:
        """Stop the cleanup thread."""
        if self._cleanup_thread:
            self._stop_cleanup.set()
            self._cleanup_thread.join(timeout=5.0)
            self._cleanup_thread = None
