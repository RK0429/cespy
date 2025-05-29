#!/usr/bin/env python
# coding=utf-8
"""Streaming API for memory-efficient raw file processing.

This module provides streaming capabilities for processing large raw files
without loading all data into memory at once.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Union

import numpy as np
from numpy.typing import NDArray

from .raw_read import RawRead, read_float32, read_float64, read_complex
from .raw_classes import DummyTrace
from ..core import constants as core_constants

_logger = logging.getLogger("cespy.RawStream")


@dataclass
class StreamConfig:
    """Configuration for streaming operations."""

    chunk_size: int = 1000  # Points per chunk
    buffer_size: int = 10  # Number of chunks to buffer
    skip_steps: int = 1  # Process every N steps (1 = process all)
    trace_filter: Optional[Callable[[str], bool]] = None  # Filter traces to process
    progress_callback: Optional[Callable[[int, int], None]] = None  # Progress reporting


class StreamProcessor(ABC):
    """Abstract base class for stream processors."""

    @abstractmethod
    def process_chunk(
        self, trace_name: str, step: int, time_data: NDArray, trace_data: NDArray
    ) -> Optional[Any]:
        """Process a chunk of data.

        Args:
            trace_name: Name of the trace
            step: Step number
            time_data: Time axis data for this chunk
            trace_data: Trace data for this chunk

        Returns:
            Optional result from processing
        """
        pass

    @abstractmethod
    def finalize(self) -> Any:
        """Finalize processing and return results.

        Returns:
            Final processing results
        """
        pass


class RawFileStreamer:
    """Streams data from raw files for memory-efficient processing.

    This class provides an iterator-based interface for processing
    large raw files without loading all data into memory.
    """

    def __init__(
        self, raw_file: Union[str, Path], config: Optional[StreamConfig] = None
    ):
        """Initialize raw file streamer.

        Args:
            raw_file: Path to raw file
            config: Streaming configuration
        """
        self.raw_file = Path(raw_file)
        self.config = config or StreamConfig()

        # Open raw file in header-only mode first
        self._raw_reader = RawRead(raw_file, headeronly=True)

        # Get file information
        self.num_traces = len(self._raw_reader._traces)
        self.num_steps = (
            len(list(self._raw_reader.get_steps())) if self._raw_reader.steps else 1
        )
        self.num_points = self._raw_reader.nPoints

        # Calculate actual chunk parameters
        self.chunk_size = min(self.config.chunk_size, self.num_points)
        self.num_chunks = (self.num_points + self.chunk_size - 1) // self.chunk_size

        _logger.info(
            "RawFileStreamer initialized: %d traces, %d steps, %d points",
            self.num_traces,
            self.num_steps,
            self.num_points,
        )

    def stream_traces(
        self,
        traces: Optional[Union[str, List[str]]] = None,
        steps: Optional[List[int]] = None,
    ) -> Iterator[Tuple[str, int, NDArray, NDArray]]:
        """Stream trace data in chunks.

        Args:
            traces: Specific traces to stream (None for all)
            steps: Specific steps to stream (None for all)

        Yields:
            Tuples of (trace_name, step, time_chunk, data_chunk)
        """
        # Determine traces to process
        if traces is None:
            trace_list = self._raw_reader.get_trace_names()
        elif isinstance(traces, str):
            trace_list = [traces]
        else:
            trace_list = traces

        # Apply trace filter if configured
        if self.config.trace_filter:
            trace_list = [t for t in trace_list if self.config.trace_filter(t)]

        # Determine steps to process
        if steps is None:
            step_list = list(range(0, self.num_steps, self.config.skip_steps))
        else:
            step_list = steps

        total_iterations = len(trace_list) * len(step_list)
        current_iteration = 0

        # Stream data
        for trace_name in trace_list:
            for step in step_list:
                # Report progress if callback provided
                if self.config.progress_callback:
                    self.config.progress_callback(current_iteration, total_iterations)

                # Stream chunks for this trace/step combination
                yield from self._stream_trace_step(trace_name, step)

                current_iteration += 1

        # Final progress report
        if self.config.progress_callback:
            self.config.progress_callback(total_iterations, total_iterations)

    def _stream_trace_step(
        self, trace_name: str, step: int
    ) -> Iterator[Tuple[str, int, NDArray, NDArray]]:
        """Stream a single trace/step combination in chunks.

        Args:
            trace_name: Name of trace to stream
            step: Step number

        Yields:
            Tuples of (trace_name, step, time_chunk, data_chunk)
        """
        # This is a simplified implementation
        # In practice, this would read directly from file in chunks

        # For now, read the full data and chunk it
        # A true streaming implementation would read chunks directly from disk
        trace = self._raw_reader.get_trace(trace_name)
        time_trace = self._raw_reader.get_trace("time")
        
        # Handle different trace types
        if isinstance(time_trace, DummyTrace):
            # DummyTrace doesn't have actual data, skip
            raise ValueError("Cannot stream from DummyTrace - no data available")
            
        if isinstance(trace, DummyTrace):
            # DummyTrace doesn't have actual data, skip
            raise ValueError("Cannot stream from DummyTrace - no data available")
            
        time_data = time_trace.get_wave(step)
        trace_data = trace.get_wave(step)

        # Yield chunks
        for chunk_idx in range(self.num_chunks):
            start_idx = chunk_idx * self.chunk_size
            end_idx = min(start_idx + self.chunk_size, self.num_points)

            time_chunk = time_data[start_idx:end_idx]
            data_chunk = trace_data[start_idx:end_idx]

            yield trace_name, step, time_chunk, data_chunk

    def process_with(self, processor: StreamProcessor) -> Any:
        """Process the raw file with a stream processor.

        Args:
            processor: StreamProcessor instance

        Returns:
            Results from processor.finalize()
        """
        # Process all traces
        for trace_name, step, time_chunk, data_chunk in self.stream_traces():
            processor.process_chunk(trace_name, step, time_chunk, data_chunk)

        # Return final results
        return processor.finalize()

    def close(self) -> None:
        """Close the streamer and clean up resources."""
        # Nothing to clean up in current implementation
        pass


# Example stream processors


class MinMaxProcessor(StreamProcessor):
    """Stream processor that tracks min/max values."""

    def __init__(self) -> None:
        """Initialize min/max processor."""
        self.results: Dict[str, Dict[int, Tuple[float, float]]] = {}

    def process_chunk(
        self, trace_name: str, step: int, time_data: NDArray, trace_data: NDArray
    ) -> None:
        """Process chunk to update min/max values."""
        if trace_name not in self.results:
            self.results[trace_name] = {}

        chunk_min = float(np.min(np.real(trace_data)))
        chunk_max = float(np.max(np.real(trace_data)))

        if step in self.results[trace_name]:
            current_min, current_max = self.results[trace_name][step]
            self.results[trace_name][step] = (
                min(current_min, chunk_min),
                max(current_max, chunk_max),
            )
        else:
            self.results[trace_name][step] = (chunk_min, chunk_max)

    def finalize(self) -> Dict[str, Dict[int, Tuple[float, float]]]:
        """Return min/max results."""
        return self.results


class AverageProcessor(StreamProcessor):
    """Stream processor that calculates averages."""

    def __init__(self) -> None:
        """Initialize average processor."""
        self.sums: Dict[str, Dict[int, float]] = {}
        self.counts: Dict[str, Dict[int, int]] = {}

    def process_chunk(
        self, trace_name: str, step: int, time_data: NDArray, trace_data: NDArray
    ) -> None:
        """Process chunk to update running averages."""
        if trace_name not in self.sums:
            self.sums[trace_name] = {}
            self.counts[trace_name] = {}

        chunk_sum = float(np.sum(np.real(trace_data)))
        chunk_count = len(trace_data)

        if step in self.sums[trace_name]:
            self.sums[trace_name][step] += chunk_sum
            self.counts[trace_name][step] += chunk_count
        else:
            self.sums[trace_name][step] = chunk_sum
            self.counts[trace_name][step] = chunk_count

    def finalize(self) -> Dict[str, Dict[int, float]]:
        """Calculate and return averages."""
        results: Dict[str, Dict[int, float]] = {}

        for trace_name in self.sums:
            results[trace_name] = {}
            for step in self.sums[trace_name]:
                results[trace_name][step] = (
                    self.sums[trace_name][step] / self.counts[trace_name][step]
                )

        return results


class ThresholdCrossingProcessor(StreamProcessor):
    """Stream processor that finds threshold crossings."""

    def __init__(self, threshold: float, rising: bool = True):
        """Initialize threshold crossing processor.

        Args:
            threshold: Threshold value
            rising: Look for rising edge (True) or falling edge (False)
        """
        self.threshold = threshold
        self.rising = rising
        self.crossings: Dict[str, Dict[int, List[float]]] = {}
        self._last_values: Dict[Tuple[str, int], float] = {}
        self._last_times: Dict[Tuple[str, int], float] = {}

    def process_chunk(
        self, trace_name: str, step: int, time_data: NDArray, trace_data: NDArray
    ) -> None:
        """Process chunk to find threshold crossings."""
        if trace_name not in self.crossings:
            self.crossings[trace_name] = {}
        if step not in self.crossings[trace_name]:
            self.crossings[trace_name][step] = []

        key = (trace_name, step)

        # Handle continuation from previous chunk
        if key in self._last_values and len(trace_data) > 0:
            # Check crossing between chunks
            last_val = self._last_values[key]
            first_val = float(np.real(trace_data[0]))

            if self.rising and last_val < self.threshold <= first_val:
                # Interpolate crossing time
                t_cross = self._interpolate_crossing(
                    self._last_times[key], float(time_data[0]), last_val, first_val
                )
                self.crossings[trace_name][step].append(t_cross)
            elif not self.rising and last_val > self.threshold >= first_val:
                # Interpolate crossing time
                t_cross = self._interpolate_crossing(
                    self._last_times[key], float(time_data[0]), last_val, first_val
                )
                self.crossings[trace_name][step].append(t_cross)

        # Find crossings within chunk
        real_data = np.real(trace_data)
        if self.rising:
            # Find where data crosses threshold going up
            mask = (real_data[:-1] < self.threshold) & (real_data[1:] >= self.threshold)
        else:
            # Find where data crosses threshold going down
            mask = (real_data[:-1] > self.threshold) & (real_data[1:] <= self.threshold)

        crossing_indices = np.where(mask)[0]

        for idx in crossing_indices:
            # Interpolate exact crossing time
            t_cross = self._interpolate_crossing(
                float(time_data[idx]),
                float(time_data[idx + 1]),
                float(real_data[idx]),
                float(real_data[idx + 1]),
            )
            self.crossings[trace_name][step].append(t_cross)

        # Store last values for next chunk
        if len(trace_data) > 0:
            self._last_values[key] = float(np.real(trace_data[-1]))
            self._last_times[key] = float(time_data[-1])

    def _interpolate_crossing(
        self, t1: float, t2: float, v1: float, v2: float
    ) -> float:
        """Interpolate the exact time of threshold crossing."""
        if v1 == v2:
            return t1

        # Linear interpolation
        fraction = (self.threshold - v1) / (v2 - v1)
        return t1 + fraction * (t2 - t1)

    def finalize(self) -> Dict[str, Dict[int, List[float]]]:
        """Return crossing times."""
        return self.crossings


class DataSamplerProcessor(StreamProcessor):
    """Stream processor that samples data at regular intervals."""

    def __init__(self, sample_rate: int):
        """Initialize data sampler.

        Args:
            sample_rate: Sample every N points
        """
        self.sample_rate = sample_rate
        self.samples: Dict[str, Dict[int, Tuple[List[float], List[float]]]] = {}
        self._point_counter: Dict[Tuple[str, int], int] = {}

    def process_chunk(
        self, trace_name: str, step: int, time_data: NDArray, trace_data: NDArray
    ) -> None:
        """Process chunk to sample data."""
        if trace_name not in self.samples:
            self.samples[trace_name] = {}
        if step not in self.samples[trace_name]:
            self.samples[trace_name][step] = ([], [])

        key = (trace_name, step)
        if key not in self._point_counter:
            self._point_counter[key] = 0

        times, values = self.samples[trace_name][step]

        # Sample points from chunk
        for i in range(len(trace_data)):
            if self._point_counter[key] % self.sample_rate == 0:
                times.append(float(time_data[i]))
                values.append(float(np.real(trace_data[i])))
            self._point_counter[key] += 1

    def finalize(self) -> Dict[str, Dict[int, Tuple[NDArray, NDArray]]]:
        """Convert lists to arrays and return."""
        results: Dict[str, Dict[int, Tuple[NDArray, NDArray]]] = {}

        for trace_name in self.samples:
            results[trace_name] = {}
            for step in self.samples[trace_name]:
                times, values = self.samples[trace_name][step]
                results[trace_name][step] = (np.array(times), np.array(values))

        return results
