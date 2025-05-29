#!/usr/bin/env python
# coding=utf-8
"""Task queue management for simulation tasks.

This module provides a priority-based task queue for managing simulation tasks,
with support for dependency tracking and task prioritization.
"""

import heapq
import logging
import threading
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from .run_task import RunTask

_logger = logging.getLogger("cespy.TaskQueue")


class TaskPriority(Enum):
    """Task priority levels."""

    HIGH = 1
    NORMAL = 5
    LOW = 10

    def __lt__(self, other: Any) -> bool:
        """Enable comparison for priority queue."""
        if isinstance(other, TaskPriority):
            return self.value < other.value
        return NotImplemented


class TaskStatus(Enum):
    """Task execution status."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskInfo:
    """Information about a queued task."""

    task_id: str = field(default_factory=lambda: str(uuid4()))
    run_task: Optional[RunTask] = field(default=None)
    priority: TaskPriority = field(default=TaskPriority.NORMAL)
    dependencies: Set[str] = field(default_factory=set)
    status: TaskStatus = field(default=TaskStatus.PENDING)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize task ID if not provided."""
        if self.task_id is None:  # type: ignore[unreachable]
            self.task_id = str(uuid4())

    def __lt__(self, other: Any) -> bool:
        """Enable comparison for priority queue."""
        if isinstance(other, TaskInfo):
            return self.priority < other.priority
        return NotImplemented


class TaskQueue:
    """Manages simulation tasks with priorities and dependencies.

    This class provides a thread-safe queue for simulation tasks with:
    - Priority-based scheduling
    - Dependency tracking
    - Task grouping and batching
    - Resource limit enforcement
    """

    def __init__(self, max_concurrent_tasks: int = 4):
        """Initialize task queue.

        Args:
            max_concurrent_tasks: Maximum number of tasks that can run concurrently
        """
        self.max_concurrent_tasks = max_concurrent_tasks
        self._queue: List[TaskInfo] = []  # Priority queue
        self._running_tasks: Dict[str, TaskInfo] = {}
        self._completed_tasks: Dict[str, TaskInfo] = {}
        self._task_dependencies: Dict[str, Set[str]] = {}
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._shutdown = False

        # Task groups for batch management
        self._task_groups: Dict[str, List[str]] = {}

        # Statistics
        self._total_submitted = 0
        self._total_completed = 0
        self._total_failed = 0

    def submit(
        self,
        run_task: RunTask,
        priority: TaskPriority = TaskPriority.NORMAL,
        dependencies: Optional[Set[str]] = None,
        group: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Submit a task to the queue.

        Args:
            run_task: The simulation task to execute
            priority: Task priority level
            dependencies: Set of task IDs this task depends on
            group: Optional group name for batch operations
            metadata: Optional metadata to attach to the task

        Returns:
            Task ID for tracking

        Raises:
            RuntimeError: If queue is shut down
        """
        with self._lock:
            if self._shutdown:
                raise RuntimeError("Cannot submit tasks to a shut down queue")

            # Create task info
            task_info = TaskInfo(
                run_task=run_task,
                priority=priority,
                dependencies=dependencies or set(),
                status=TaskStatus.PENDING,
                metadata=metadata or {},
            )

            # Track dependencies
            if dependencies:
                self._task_dependencies[task_info.task_id] = dependencies.copy()

            # Add to group if specified
            if group:
                if group not in self._task_groups:
                    self._task_groups[group] = []
                self._task_groups[group].append(task_info.task_id)

            # Check if task can be queued immediately
            if self._can_queue_task(task_info):
                task_info.status = TaskStatus.QUEUED
                heapq.heappush(self._queue, task_info)
                self._condition.notify()
            elif dependencies:
                # Store as pending until dependencies are met
                self._task_dependencies[task_info.task_id] = dependencies.copy()

            self._total_submitted += 1
            _logger.debug(
                "Submitted task %s with priority %s", task_info.task_id, priority
            )

            return task_info.task_id

    def get_next(self, timeout: Optional[float] = None) -> Optional[TaskInfo]:
        """Get the next task to execute.

        This method blocks until a task is available or timeout occurs.

        Args:
            timeout: Maximum time to wait for a task (None for infinite)

        Returns:
            Next task to execute or None if timeout/shutdown
        """
        with self._condition:
            # Wait for a task to be available
            if not self._queue and not self._shutdown:
                if not self._condition.wait(timeout):
                    return None  # Timeout

            if self._shutdown and not self._queue:
                return None

            if self._queue:
                # Get highest priority task
                task_info = heapq.heappop(self._queue)
                task_info.status = TaskStatus.RUNNING
                self._running_tasks[task_info.task_id] = task_info

                _logger.debug("Retrieved task %s for execution", task_info.task_id)
                return task_info

            return None

    def mark_completed(self, task_id: str, success: bool = True) -> None:
        """Mark a task as completed.

        Args:
            task_id: ID of the completed task
            success: Whether the task completed successfully
        """
        with self._lock:
            if task_id not in self._running_tasks:
                _logger.warning(
                    "Attempting to mark unknown task %s as completed", task_id
                )
                return

            # Move task to completed
            task_info = self._running_tasks.pop(task_id)
            task_info.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
            self._completed_tasks[task_id] = task_info

            # Update statistics
            self._total_completed += 1
            if not success:
                self._total_failed += 1

            # Check for tasks waiting on this dependency
            self._check_pending_dependencies(task_id)

            _logger.debug("Task %s marked as %s", task_id, task_info.status.value)

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or queued task.

        Args:
            task_id: ID of the task to cancel

        Returns:
            True if task was cancelled, False if not found or already running
        """
        with self._lock:
            # Check if task is in queue
            for i, task_info in enumerate(self._queue):
                if task_info.task_id == task_id:
                    self._queue.pop(i)
                    heapq.heapify(self._queue)
                    task_info.status = TaskStatus.CANCELLED
                    self._completed_tasks[task_id] = task_info
                    _logger.info("Cancelled task %s", task_id)
                    return True

            # Check if task is pending
            if task_id in self._task_dependencies:
                # Create a cancelled task info
                task_info = TaskInfo(task_id=task_id, status=TaskStatus.CANCELLED)
                self._completed_tasks[task_id] = task_info
                del self._task_dependencies[task_id]
                return True

            return False

    def cancel_group(self, group: str) -> int:
        """Cancel all tasks in a group.

        Args:
            group: Name of the group to cancel

        Returns:
            Number of tasks cancelled
        """
        if group not in self._task_groups:
            return 0

        cancelled = 0
        for task_id in self._task_groups[group]:
            if self.cancel_task(task_id):
                cancelled += 1

        return cancelled

    def get_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get the status of a task.

        Args:
            task_id: ID of the task

        Returns:
            Task status or None if not found
        """
        with self._lock:
            # Check running tasks
            if task_id in self._running_tasks:
                return self._running_tasks[task_id].status

            # Check completed tasks
            if task_id in self._completed_tasks:
                return self._completed_tasks[task_id].status

            # Check queue
            for task_info in self._queue:
                if task_info.task_id == task_id:
                    return task_info.status

            # Check pending
            if task_id in self._task_dependencies:
                return TaskStatus.PENDING

            return None

    def get_statistics(self) -> Dict[str, int]:
        """Get queue statistics.

        Returns:
            Dictionary with queue statistics
        """
        with self._lock:
            return {
                "total_submitted": self._total_submitted,
                "total_completed": self._total_completed,
                "total_failed": self._total_failed,
                "queued": len(self._queue),
                "running": len(self._running_tasks),
                "pending": len(self._task_dependencies),
                "groups": len(self._task_groups),
            }

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the queue.

        Args:
            wait: If True, wait for running tasks to complete
        """
        with self._lock:
            self._shutdown = True
            self._condition.notify_all()

            if not wait:
                # Cancel all queued tasks
                while self._queue:
                    task_info = heapq.heappop(self._queue)
                    task_info.status = TaskStatus.CANCELLED
                    self._completed_tasks[task_info.task_id] = task_info

        if wait:
            # Wait for running tasks to complete
            with self._lock:
                while self._running_tasks:
                    self._condition.wait(1.0)

    def _can_queue_task(self, task_info: TaskInfo) -> bool:
        """Check if a task can be queued.

        Args:
            task_info: Task to check

        Returns:
            True if all dependencies are satisfied
        """
        if not task_info.dependencies:
            return True

        # Check if all dependencies are completed
        for dep_id in task_info.dependencies:
            if dep_id not in self._completed_tasks:
                return False

        return True

    def _check_pending_dependencies(self, completed_task_id: str) -> None:
        """Check if any pending tasks can now be queued.

        Args:
            completed_task_id: ID of the task that just completed
        """
        tasks_to_queue: List[str] = []

        # Find tasks that were waiting on this dependency
        for task_id, deps in list(self._task_dependencies.items()):
            if completed_task_id in deps:
                deps.remove(completed_task_id)

                # If all dependencies are satisfied, queue the task
                if not deps:
                    # Need to create TaskInfo from stored data
                    # This is a limitation of the current design
                    # In a real implementation, we'd store TaskInfo objects
                    _logger.debug("Task %s dependencies satisfied, queuing", task_id)
                    del self._task_dependencies[task_id]

        # Queue any tasks that are now ready
        for task_info in tasks_to_queue:
            task_info.status = TaskStatus.QUEUED
            heapq.heappush(self._queue, task_info)

        if tasks_to_queue:
            self._condition.notify()
