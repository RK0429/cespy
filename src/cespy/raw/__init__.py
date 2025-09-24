"""Raw waveform file handling modules.

This module provides functionality for reading and writing SPICE raw waveform files,
with support for lazy loading, streaming, and optimized binary parsing for handling
large simulation data efficiently.
"""

from .raw_binary_parser import BinaryFormat, DataFormat, OptimizedBinaryParser
from .raw_classes import Axis, DataSet, DummyTrace, SpiceReadException, TraceRead
from .raw_data_cache import (
    CachePolicy,
    LFUPolicy,
    LRUPolicy,
    MultiLevelCache,
    RawDataCache,
)
from .raw_read import RawRead
from .raw_read_lazy import LazyTrace, RawReadLazy
from .raw_stream import (
    AverageProcessor,
    MinMaxProcessor,
    RawFileStreamer,
    StreamConfig,
    StreamProcessor,
)
from .raw_write import RawWrite, Trace

__all__ = [
    "AverageProcessor",
    "Axis",
    "BinaryFormat",
    "CachePolicy",
    "DataFormat",
    "DataSet",
    "DummyTrace",
    "LFUPolicy",
    "LRUPolicy",
    "LazyTrace",
    "MinMaxProcessor",
    "MultiLevelCache",
    # Binary parsing
    "OptimizedBinaryParser",
    # Caching
    "RawDataCache",
    # Streaming
    "RawFileStreamer",
    # Core classes
    "RawRead",
    # Lazy loading
    "RawReadLazy",
    "RawWrite",
    "SpiceReadException",
    "StreamConfig",
    "StreamProcessor",
    "Trace",
    "TraceRead",
]
