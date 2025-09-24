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
    # Core classes
    "RawRead",
    "RawWrite",
    "Trace",
    "TraceRead",
    "DataSet",
    "Axis",
    "DummyTrace",
    "SpiceReadException",
    # Lazy loading
    "RawReadLazy",
    "LazyTrace",
    # Streaming
    "RawFileStreamer",
    "StreamProcessor",
    "StreamConfig",
    "MinMaxProcessor",
    "AverageProcessor",
    # Caching
    "RawDataCache",
    "MultiLevelCache",
    "CachePolicy",
    "LRUPolicy",
    "LFUPolicy",
    # Binary parsing
    "OptimizedBinaryParser",
    "DataFormat",
    "BinaryFormat",
]
