"""Raw waveform file handling modules.

This module provides functionality for reading and writing SPICE raw waveform files,
with support for lazy loading, streaming, and optimized binary parsing for handling
large simulation data efficiently.
"""

from .raw_classes import Axis, DataSet, DummyTrace, SpiceReadException, TraceRead
from .raw_read import RawRead
from .raw_write import RawWrite, Trace
from .raw_read_lazy import RawReadLazy, LazyTrace
from .raw_stream import (
    RawFileStreamer,
    StreamProcessor,
    StreamConfig,
    MinMaxProcessor,
    AverageProcessor,
)
from .raw_data_cache import (
    RawDataCache,
    MultiLevelCache,
    CachePolicy,
    LRUPolicy,
    LFUPolicy,
)
from .raw_binary_parser import OptimizedBinaryParser, DataFormat, BinaryFormat

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
