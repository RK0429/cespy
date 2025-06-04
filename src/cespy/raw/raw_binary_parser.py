#!/usr/bin/env python
# coding=utf-8
"""Optimized binary parsing for raw files using numpy operations.

This module provides high-performance binary parsing for SPICE raw files
using numpy's efficient array operations instead of element-by-element reading.
"""

import logging
import struct
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, BinaryIO, Literal

import numpy as np
from numpy.typing import NDArray

_logger = logging.getLogger("cespy.RawBinaryParser")


class DataFormat(Enum):
    """Binary data formats in raw files."""

    FLOAT32 = "float32"
    FLOAT64 = "float64"
    COMPLEX64 = "complex64"  # 2 x float32
    COMPLEX128 = "complex128"  # 2 x float64


@dataclass
class BinaryFormat:
    """Description of binary data format."""

    format: DataFormat
    bytes_per_value: int
    numpy_dtype: np.dtype[Any]
    struct_format: str  # For single value reading


# Format definitions
BINARY_FORMATS = {
    DataFormat.FLOAT32: BinaryFormat(
        format=DataFormat.FLOAT32,
        bytes_per_value=4,
        numpy_dtype=np.dtype(np.float32),
        struct_format="f",
    ),
    DataFormat.FLOAT64: BinaryFormat(
        format=DataFormat.FLOAT64,
        bytes_per_value=8,
        numpy_dtype=np.dtype(np.float64),
        struct_format="d",
    ),
    DataFormat.COMPLEX64: BinaryFormat(
        format=DataFormat.COMPLEX64,
        bytes_per_value=8,
        numpy_dtype=np.dtype(np.complex64),
        struct_format="ff",
    ),
    DataFormat.COMPLEX128: BinaryFormat(
        format=DataFormat.COMPLEX128,
        bytes_per_value=16,
        numpy_dtype=np.dtype(np.complex128),
        struct_format="dd",
    ),
}


class OptimizedBinaryParser:
    """Optimized parser for raw file binary data.

    This parser uses numpy operations for bulk reading of binary data,
    significantly improving performance for large files.
    """

    def __init__(self, file_path: Union[str, Path]):
        """Initialize binary parser.

        Args:
            file_path: Path to raw file
        """
        self.file_path = Path(file_path)
        self._file_handle: Optional[BinaryIO] = None

        # Cache file size
        self.file_size = self.file_path.stat().st_size

        _logger.debug(
            "OptimizedBinaryParser initialized for %s (%d bytes)",
            file_path,
            self.file_size,
        )

    def read_block(
        self,
        offset: int,
        count: int,
        format: DataFormat,
        byte_order: str = "<",  # Little-endian by default
    ) -> NDArray[np.float64]:
        """Read a block of values efficiently.

        Args:
            offset: Byte offset in file
            count: Number of values to read
            format: Data format
            byte_order: Byte order ('<' for little-endian, '>' for big-endian)

        Returns:
            Numpy array with the data
        """
        fmt_info = BINARY_FORMATS[format]
        num_bytes = count * fmt_info.bytes_per_value

        # Check bounds
        if offset + num_bytes > self.file_size:
            raise ValueError(
                f"Read would exceed file size: {offset + num_bytes} > {self.file_size}"
            )

        # Read raw bytes
        if self._file_handle is None:
            self._file_handle = open(self.file_path, "rb")

        self._file_handle.seek(offset)
        raw_bytes = self._file_handle.read(num_bytes)

        if len(raw_bytes) < num_bytes:
            raise IOError(f"Could only read {len(raw_bytes)} of {num_bytes} bytes")

        # Convert to numpy array
        dtype = fmt_info.numpy_dtype
        if byte_order != "<":
            # Adjust dtype for big-endian
            dtype = dtype.newbyteorder(">")

        return np.frombuffer(raw_bytes, dtype=dtype)

    def read_interleaved(
        self,
        offset: int,
        num_traces: int,
        num_points: int,
        trace_formats: List[DataFormat],
        byte_order: str = "<",
    ) -> List[NDArray[Any]]:
        """Read interleaved trace data efficiently.

        This handles the common case where trace data is interleaved:
        [t0_v0, t1_v0, t2_v0, ..., tn_v0, t0_v1, t1_v1, ...]

        Args:
            offset: Starting byte offset
            num_traces: Number of traces
            num_points: Number of points per trace
            trace_formats: Format for each trace
            byte_order: Byte order

        Returns:
            List of numpy arrays, one per trace
        """
        if len(trace_formats) != num_traces:
            raise ValueError(f"Expected {num_traces} formats, got {len(trace_formats)}")

        # Calculate total size
        bytes_per_sample = sum(
            BINARY_FORMATS[fmt].bytes_per_value for fmt in trace_formats
        )
        total_bytes = num_points * bytes_per_sample

        # Read all data at once
        if self._file_handle is None:
            self._file_handle = open(self.file_path, "rb")

        self._file_handle.seek(offset)
        raw_bytes = self._file_handle.read(total_bytes)

        if len(raw_bytes) < total_bytes:
            raise IOError(f"Could only read {len(raw_bytes)} of {total_bytes} bytes")

        # Parse interleaved data
        traces = []
        byte_offset = 0

        for trace_idx, fmt in enumerate(trace_formats):
            fmt_info = BINARY_FORMATS[fmt]
            trace_data = np.zeros(num_points, dtype=fmt_info.numpy_dtype)

            # Extract this trace's data
            for point_idx in range(num_points):
                sample_offset = point_idx * bytes_per_sample + byte_offset
                value_bytes = raw_bytes[
                    sample_offset : sample_offset + fmt_info.bytes_per_value
                ]

                if fmt == DataFormat.COMPLEX64:
                    real, imag = struct.unpack(f"{byte_order}ff", value_bytes)
                    trace_data[point_idx] = complex(real, imag)
                elif fmt == DataFormat.COMPLEX128:
                    real, imag = struct.unpack(f"{byte_order}dd", value_bytes)
                    trace_data[point_idx] = complex(real, imag)
                else:
                    value = struct.unpack(
                        f"{byte_order}{fmt_info.struct_format}", value_bytes
                    )[0]
                    trace_data[point_idx] = value

            traces.append(trace_data)
            byte_offset += fmt_info.bytes_per_value

        return traces

    def read_sequential(
        self,
        offset: int,
        num_traces: int,
        num_points: int,
        trace_formats: List[DataFormat],
        byte_order: str = "<",
    ) -> List[NDArray[Any]]:
        """Read sequential trace data efficiently.

        This handles the case where all data for one trace is stored
        before moving to the next trace:
        [t0_v0, t0_v1, ..., t0_vn, t1_v0, t1_v1, ..., t1_vn, ...]

        Args:
            offset: Starting byte offset
            num_traces: Number of traces
            num_points: Number of points per trace
            trace_formats: Format for each trace
            byte_order: Byte order

        Returns:
            List of numpy arrays, one per trace
        """
        traces = []
        current_offset = offset

        for trace_idx, fmt in enumerate(trace_formats):
            # Read entire trace at once
            trace_data = self.read_block(current_offset, num_points, fmt, byte_order)
            traces.append(trace_data)

            # Update offset for next trace
            fmt_info = BINARY_FORMATS[fmt]
            current_offset += num_points * fmt_info.bytes_per_value

        return traces

    def read_fast_access(
        self,
        offset: int,
        num_traces: int,
        num_points: int,
        trace_formats: List[DataFormat],
        byte_order: str = "<",
    ) -> List[NDArray[Any]]:
        """Read FastAccess format data.

        In FastAccess format, data is organized for efficient access:
        all values for trace 0, then all values for trace 1, etc.

        Args:
            offset: Starting byte offset
            num_traces: Number of traces
            num_points: Number of points per trace
            trace_formats: Format for each trace
            byte_order: Byte order

        Returns:
            List of numpy arrays, one per trace
        """
        # FastAccess is essentially sequential format
        return self.read_sequential(
            offset, num_traces, num_points, trace_formats, byte_order
        )

    def detect_format(
        self, offset: int, sample_size: int = 1000
    ) -> Tuple[DataFormat, str]:
        """Auto-detect binary format by analyzing data patterns.

        Args:
            offset: Byte offset to start detection
            sample_size: Number of values to sample

        Returns:
            Tuple of (detected_format, byte_order)
        """
        if self._file_handle is None:
            self._file_handle = open(self.file_path, "rb")

        # Read sample data
        self._file_handle.seek(offset)
        sample_bytes = self._file_handle.read(
            sample_size * 16
        )  # Max size for complex128

        # Try different formats and check for reasonable values
        best_format = DataFormat.FLOAT32
        best_order = "<"
        best_score = float("inf")

        for fmt in DataFormat:
            for order in ["<", ">"]:
                try:
                    # Parse as this format
                    fmt_info = BINARY_FORMATS[fmt]
                    num_values = len(sample_bytes) // fmt_info.bytes_per_value

                    if num_values < 10:
                        continue

                    # Create dtype with byte order
                    dtype = fmt_info.numpy_dtype
                    if order == ">":
                        dtype = dtype.newbyteorder(">")

                    # Parse values
                    values = np.frombuffer(
                        sample_bytes[: num_values * fmt_info.bytes_per_value],
                        dtype=dtype,
                    )

                    # Check if values are reasonable
                    if np.iscomplex(values).any():
                        # Complex values
                        real_part = np.real(values)
                        imag_part = np.imag(values)

                        # Check for NaN or Inf
                        if np.isnan(real_part).any() or np.isnan(imag_part).any():
                            continue
                        if np.isinf(real_part).any() or np.isinf(imag_part).any():
                            continue

                        # Calculate score based on value distribution
                        score = float(np.std(real_part) + np.std(imag_part))
                    else:
                        # Real values
                        # Check for NaN or Inf
                        if np.isnan(values).any() or np.isinf(values).any():
                            continue

                        # Calculate score based on value distribution
                        # Good data typically has some variation but not extreme
                        score = float(np.std(values))

                        # Penalize if all values are zero or very small
                        if np.all(np.abs(values) < 1e-30):
                            score = float("inf")

                    if score < best_score:
                        best_score = score
                        best_format = fmt
                        best_order = order

                except Exception:
                    continue

        _logger.info(
            "Detected format: %s, byte order: %s", best_format.value, best_order
        )
        return best_format, best_order

    def create_memory_map(
        self,
        offset: int,
        shape: Tuple[int, ...],
        dtype: np.dtype[Any],
        mode: Literal["r", "r+", "w+", "c"] = "r",
    ) -> np.memmap[Any, np.dtype[np.float64]]:
        """Create a memory-mapped array for efficient large file access.

        Args:
            offset: Byte offset in file
            shape: Shape of the array
            dtype: Data type
            mode: Access mode ('r' for read-only)

        Returns:
            Memory-mapped numpy array
        """
        return np.memmap(
            self.file_path, dtype=dtype, mode=mode, offset=offset, shape=shape
        )

    def close(self) -> None:
        """Close file handle."""
        if self._file_handle is not None:
            self._file_handle.close()
            self._file_handle = None

    def __enter__(self) -> "OptimizedBinaryParser":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()

    def __del__(self) -> None:
        """Ensure file is closed on deletion."""
        self.close()


def benchmark_parser(
    file_path: Path, num_traces: int = 10, num_points: int = 100000
) -> Dict[str, float]:
    """Benchmark different parsing methods.

    Args:
        file_path: Path to raw file
        num_traces: Number of traces to read
        num_points: Number of points per trace

    Returns:
        Dictionary with timing results
    """
    import time

    results = {}

    # Test optimized parser
    with OptimizedBinaryParser(file_path) as parser:
        # Warm up
        parser.read_block(0, 100, DataFormat.FLOAT32)

        # Test block read
        start = time.time()
        _data = parser.read_block(0, num_traces * num_points, DataFormat.FLOAT32)
        del _data  # Only needed for timing
        results["block_read"] = time.time() - start

        # Test interleaved read
        formats = [DataFormat.FLOAT32] * num_traces
        start = time.time()
        _traces = parser.read_interleaved(0, num_traces, num_points, formats)
        del _traces  # Only needed for timing
        results["interleaved_read"] = time.time() - start

        # Test sequential read
        start = time.time()
        _traces = parser.read_sequential(0, num_traces, num_points, formats)
        del _traces  # Only needed for timing
        results["sequential_read"] = time.time() - start

    # Calculate throughput
    total_bytes = num_traces * num_points * 4  # float32
    for method, time_taken in results.items():
        throughput_mbps = (total_bytes / 1024 / 1024) / time_taken
        _logger.info(
            "%s: %.3f seconds (%.1f MB/s)", method, time_taken, throughput_mbps
        )

    return results
