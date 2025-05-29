#!/usr/bin/env python
# coding=utf-8
"""Lazy loading implementation for large raw files.

This module provides a lazy-loading version of RawRead that only loads
data when it's actually accessed, significantly reducing memory usage
for large simulation files.
"""

import logging
import mmap
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, BinaryIO

import numpy as np
from numpy.typing import NDArray

from .raw_read import RawRead, read_float32, read_float64, read_complex
from .raw_classes import Axis, TraceRead, SpiceReadException
from ..core import constants as core_constants

_logger = logging.getLogger("cespy.RawReadLazy")


@dataclass
class TraceInfo:
    """Information about a trace in the raw file."""

    name: str
    index: int
    var_type: str
    step_info: Dict[int, Tuple[int, int]] = field(
        default_factory=dict
    )  # step -> (offset, length)


class LazyTrace:
    """Lazy-loaded trace that reads data on demand."""

    def __init__(
        self,
        trace_info: TraceInfo,
        file_path: Path,
        is_complex: bool,
        is_float64: bool,
        mmap_file: Optional[mmap.mmap] = None,
    ) -> None:
        """Initialize lazy trace.

        Args:
            trace_info: Information about the trace
            file_path: Path to the raw file
            is_complex: Whether data is complex
            is_float64: Whether to use float64 (vs float32)
            mmap_file: Optional memory-mapped file for efficient access
        """
        self.info = trace_info
        self.file_path = file_path
        self.is_complex = is_complex
        self.is_float64 = is_float64
        self.mmap_file = mmap_file
        self._cache: Dict[int, NDArray] = {}  # Cache loaded data by step

        # Determine data size
        if is_complex:
            self.bytes_per_point = 16  # 2 * 8 bytes
        elif is_float64:
            self.bytes_per_point = 8
        else:
            self.bytes_per_point = 4

    @property
    def name(self) -> str:
        """Get trace name."""
        return self.info.name

    def get_wave(self, step: int = 0) -> NDArray:
        """Get waveform data for a specific step.

        Args:
            step: Step number

        Returns:
            Numpy array with trace data
        """
        # Check cache first
        if step in self._cache:
            return self._cache[step]

        # Get offset and length for this step
        if step not in self.info.step_info:
            raise ValueError(f"Step {step} not found for trace {self.name}")

        offset, num_points = self.info.step_info[step]

        # Read data
        if self.mmap_file is not None:
            # Use memory-mapped file
            data = self._read_from_mmap(offset, num_points)
        else:
            # Use regular file reading
            data = self._read_from_file(offset, num_points)

        # Cache the result
        self._cache[step] = data

        return data

    def _read_from_mmap(self, offset: int, num_points: int) -> NDArray:
        """Read data from memory-mapped file."""
        # Calculate byte range
        start_byte = offset
        num_bytes = num_points * self.bytes_per_point

        # Extract bytes
        raw_bytes = self.mmap_file[start_byte : start_byte + num_bytes]

        # Convert to numpy array
        if self.is_complex:
            dtype: Any = np.complex128
        elif self.is_float64:
            dtype = np.float64
        else:
            dtype = np.float32

        return np.frombuffer(raw_bytes, dtype=dtype)

    def _read_from_file(self, offset: int, num_points: int) -> NDArray:
        """Read data from file."""
        with open(self.file_path, "rb") as f:
            f.seek(offset)

            if self.is_complex:
                # Read complex values
                data = np.zeros(num_points, dtype=np.complex128)
                for i in range(num_points):
                    data[i] = read_complex(f)
            elif self.is_float64:
                # Read float64 values
                data = np.zeros(num_points, dtype=np.float64)
                for i in range(num_points):
                    data[i] = read_float64(f)
            else:
                # Read float32 values
                data = np.zeros(num_points, dtype=np.float32)
                for i in range(num_points):
                    data[i] = read_float32(f)

        return data

    def clear_cache(self, step: Optional[int] = None) -> None:
        """Clear cached data.

        Args:
            step: Specific step to clear, or None to clear all
        """
        if step is None:
            self._cache.clear()
        elif step in self._cache:
            del self._cache[step]

    def get_memory_usage(self) -> int:
        """Get approximate memory usage in bytes."""
        total = 0
        for data in self._cache.values():
            total += data.nbytes
        return total


class RawReadLazy(RawRead):
    """Lazy-loading version of RawRead for handling large files efficiently.

    This class extends RawRead to provide lazy loading of trace data,
    only reading from disk when specific traces are accessed.
    """

    def __init__(
        self,
        raw_filename: Union[str, Path],
        traces_to_read: Union[str, List[str], None] = "*",
        dialect: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize lazy raw file reader.

        Args:
            raw_filename: Path to raw file
            traces_to_read: Traces to prepare for reading
            dialect: Simulator dialect
            **kwargs: Additional arguments
        """
        self.use_mmap = kwargs.pop("use_mmap", True)
        self.cache_size_limit = kwargs.pop(
            "cache_size_limit", 1024 * 1024 * 1024
        )  # 1GB default

        # Store file path
        self.file_path = Path(raw_filename)

        # Memory-mapped file handle
        self.mmap_file: Optional[mmap.mmap] = None
        self._file_handle: Optional[BinaryIO] = None

        # Lazy trace storage
        self._lazy_traces: Dict[str, LazyTrace] = {}
        self._trace_info: Dict[str, TraceInfo] = {}

        # Initialize parent with headeronly=True to avoid loading data
        kwargs["headeronly"] = True
        super().__init__(raw_filename, traces_to_read, dialect, **kwargs)

        # After header is read, prepare lazy traces
        self._prepare_lazy_traces()

        _logger.info("RawReadLazy initialized for %s", raw_filename)

    def _prepare_lazy_traces(self) -> None:
        """Prepare lazy trace information without loading data."""
        # Open memory-mapped file if requested
        if self.use_mmap and self.file_path.exists():
            try:
                self._file_handle = open(self.file_path, "rb")
                self.mmap_file = mmap.mmap(
                    self._file_handle.fileno(), 0, access=mmap.ACCESS_READ
                )
                _logger.debug("Memory-mapped file opened")
            except Exception as e:
                _logger.warning("Failed to create memory map: %s", e)
                self.use_mmap = False

        # Prepare trace information
        for trace_name in self.get_trace_names():
            trace = self.get_trace(trace_name)

            # Create trace info
            trace_index = 0  # Will need to be set properly based on trace order
            for i, name in enumerate(self.get_trace_names()):
                if name == trace_name:
                    trace_index = i
                    break

            info = TraceInfo(
                name=trace_name,
                index=trace_index,
                var_type=trace.whattype if hasattr(trace, "whattype") else "unknown",
            )

            # Calculate offsets for each step
            # This is simplified - actual implementation would need to parse file structure
            num_steps = len(list(self.get_steps())) if self.steps else 1
            for step in range(num_steps):
                # Calculate offset based on file structure
                # This would need to be adapted based on actual raw file format
                offset = self._calculate_trace_offset(trace_index, step)
                num_points = self.nPoints

                info.step_info[step] = (offset, num_points)

            self._trace_info[trace_name] = info

            # Create lazy trace
            is_complex = (
                trace.numerical_type == "complex"
                if hasattr(trace, "numerical_type")
                else False
            )
            is_float64 = trace_index == 0  # X-axis usually float64

            lazy_trace = LazyTrace(
                trace_info=info,
                file_path=self.file_path,
                is_complex=is_complex,
                is_float64=is_float64,
                mmap_file=self.mmap_file,
            )

            self._lazy_traces[trace_name] = lazy_trace

    def get_trace(self, trace_name: str) -> Union[TraceRead, LazyTrace]:
        """Get a trace by name.

        Returns LazyTrace instead of TraceRead for lazy loading.

        Args:
            trace_name: Name of the trace

        Returns:
            LazyTrace object
        """
        if trace_name in self._lazy_traces:
            return self._lazy_traces[trace_name]

        # Fall back to parent implementation
        return super().get_trace(trace_name)

    def get_wave(self, trace_name: str, step: int = 0) -> NDArray:
        """Get waveform data for a trace.

        Args:
            trace_name: Name of the trace
            step: Step number

        Returns:
            Numpy array with waveform data
        """
        if trace_name in self._lazy_traces:
            return self._lazy_traces[trace_name].get_wave(step)

        # Fall back to parent implementation
        trace = self.get_trace(trace_name)
        return trace.get_wave(step)

    def preload_traces(
        self, trace_names: Union[str, List[str]], steps: Optional[List[int]] = None
    ) -> None:
        """Preload specific traces into memory.

        Args:
            trace_names: Trace name(s) to preload
            steps: Specific steps to preload (None for all)
        """
        if isinstance(trace_names, str):
            trace_names = [trace_names]

        if steps is None:
            steps = list(range(self.nSteps))

        for trace_name in trace_names:
            if trace_name in self._lazy_traces:
                lazy_trace = self._lazy_traces[trace_name]
                for step in steps:
                    # This will load and cache the data
                    lazy_trace.get_wave(step)

    def clear_cache(self, trace_name: Optional[str] = None) -> None:
        """Clear cached trace data.

        Args:
            trace_name: Specific trace to clear, or None for all
        """
        if trace_name is None:
            # Clear all caches
            for lazy_trace in self._lazy_traces.values():
                lazy_trace.clear_cache()
        elif trace_name in self._lazy_traces:
            self._lazy_traces[trace_name].clear_cache()

    def get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage statistics.

        Returns:
            Dictionary with memory usage information
        """
        stats = {
            "total_cached_bytes": 0,
            "traces_cached": {},
            "cache_size_limit": self.cache_size_limit,
        }

        for trace_name, lazy_trace in self._lazy_traces.items():
            usage = lazy_trace.get_memory_usage()
            if usage > 0:
                stats["traces_cached"][trace_name] = usage
                stats["total_cached_bytes"] += usage

        stats["cache_usage_percent"] = (
            stats["total_cached_bytes"] / self.cache_size_limit * 100
            if self.cache_size_limit > 0
            else 0
        )

        return stats

    def _calculate_trace_offset(self, trace_index: int, step: int) -> int:
        """Calculate byte offset for a trace in the file.

        This is a simplified implementation - actual calculation would
        depend on the specific raw file format.

        Args:
            trace_index: Index of the trace
            step: Step number

        Returns:
            Byte offset in file
        """
        # This needs to be implemented based on actual file format
        # For now, return a placeholder

        # Simplified calculation assuming:
        # - Binary data starts at self.binary_start
        # - Data is organized by step, then by trace
        # - Each trace has self.nPoints data points

        bytes_per_point = 4  # float32 by default
        # Determine complex from raw_params or a reasonable default
        plotname = self.raw_params.get("Plotname", "")
        is_complex = "AC" in plotname.upper()

        if is_complex:
            bytes_per_point = 16
        elif trace_index == 0:  # X-axis
            bytes_per_point = 8

        # Calculate offset
        # This is a simplified formula - actual implementation would be more complex
        num_traces = len(self.get_trace_names())
        points_per_step = self.nPoints * num_traces
        step_offset = step * points_per_step * bytes_per_point
        trace_offset = trace_index * self.nPoints * bytes_per_point

        # Use a reasonable binary start offset - this would need to be calculated properly
        binary_start = 1024  # Approximate header size
        return binary_start + step_offset + trace_offset

    def close(self) -> None:
        """Close file handles and clean up resources."""
        # Clear all caches
        self.clear_cache()

        # Close memory map
        if self.mmap_file is not None:
            self.mmap_file.close()
            self.mmap_file = None

        # Close file handle
        if self._file_handle is not None:
            self._file_handle.close()
            self._file_handle = None

        _logger.debug("RawReadLazy closed")

    def __enter__(self) -> "RawReadLazy":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()

    def __del__(self) -> None:
        """Destructor to ensure cleanup."""
        try:
            self.close()
        except:
            pass
