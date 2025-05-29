#!/usr/bin/env python
# coding=utf-8
"""Raw data cache for frequently accessed waveform data.

This module provides caching functionality for raw file data to improve
performance when repeatedly accessing the same traces.
"""

import logging
import pickle
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from numpy.typing import NDArray

_logger = logging.getLogger("cespy.RawDataCache")


@dataclass
class CacheEntry:
    """Entry in the raw data cache."""

    data: NDArray
    access_count: int = 0
    last_access: float = field(default_factory=time.time)
    size_bytes: int = 0

    def __post_init__(self):
        """Calculate size after initialization."""
        if isinstance(self.data, np.ndarray):
            self.size_bytes = self.data.nbytes


class CachePolicy:
    """Cache eviction policy interface."""

    def should_evict(self, cache: "RawDataCache", key: str) -> bool:
        """Determine if an entry should be evicted.

        Args:
            cache: The cache instance
            key: Key to check

        Returns:
            True if entry should be evicted
        """
        return False

    def on_access(self, cache: "RawDataCache", key: str) -> None:
        """Called when an entry is accessed.

        Args:
            cache: The cache instance
            key: Key that was accessed
        """
        pass


class LRUPolicy(CachePolicy):
    """Least Recently Used eviction policy."""

    def should_evict(self, cache: "RawDataCache", key: str) -> bool:
        """Evict least recently used entries when cache is full."""
        if cache.get_size() <= cache.max_size:
            return False

        # Find LRU entry
        oldest_time = float("inf")
        oldest_key = None

        for k, entry in cache._cache.items():
            if entry.last_access < oldest_time:
                oldest_time = entry.last_access
                oldest_key = k

        return key == oldest_key

    def on_access(self, cache: "RawDataCache", key: str) -> None:
        """Update access time."""
        if key in cache._cache:
            cache._cache[key].last_access = time.time()


class LFUPolicy(CachePolicy):
    """Least Frequently Used eviction policy."""

    def should_evict(self, cache: "RawDataCache", key: str) -> bool:
        """Evict least frequently used entries when cache is full."""
        if cache.get_size() <= cache.max_size:
            return False

        # Find LFU entry
        min_count = float("inf")
        lfu_key = None

        for k, entry in cache._cache.items():
            if entry.access_count < min_count:
                min_count = entry.access_count
                lfu_key = k

        return key == lfu_key

    def on_access(self, cache: "RawDataCache", key: str) -> None:
        """Increment access count."""
        if key in cache._cache:
            cache._cache[key].access_count += 1


class RawDataCache:
    """Cache for frequently accessed raw file data.

    This class provides an in-memory cache for waveform data with
    configurable eviction policies and persistence support.
    """

    def __init__(
        self,
        max_size: int = 1024 * 1024 * 1024,  # 1GB default
        policy: Optional[CachePolicy] = None,
        persist_path: Optional[Path] = None,
    ):
        """Initialize raw data cache.

        Args:
            max_size: Maximum cache size in bytes
            policy: Cache eviction policy (default: LRU)
            persist_path: Optional path for cache persistence
        """
        self.max_size = max_size
        self.policy = policy or LRUPolicy()
        self.persist_path = persist_path

        # Use OrderedDict to maintain insertion order
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()

        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0

        # Load persisted cache if available
        if persist_path and persist_path.exists():
            self._load_cache()

        _logger.info(
            "RawDataCache initialized with %d MB limit", max_size / 1024 / 1024
        )

    def get(self, key: str) -> Optional[NDArray]:
        """Get data from cache.

        Args:
            key: Cache key

        Returns:
            Cached data or None if not found
        """
        if key in self._cache:
            self._hits += 1
            self.policy.on_access(self, key)

            # Move to end for LRU (most recently used)
            self._cache.move_to_end(key)

            return self._cache[key].data
        else:
            self._misses += 1
            return None

    def put(self, key: str, data: NDArray) -> None:
        """Put data into cache.

        Args:
            key: Cache key
            data: Data to cache
        """
        # Check if we need to evict
        entry = CacheEntry(data=data)

        # Evict entries if needed
        while self.get_size() + entry.size_bytes > self.max_size:
            if not self._evict_one():
                _logger.warning("Cannot evict enough data to fit new entry")
                return

        # Add to cache
        self._cache[key] = entry
        self.policy.on_access(self, key)

        _logger.debug("Cached %s (%d bytes)", key, entry.size_bytes)

    def get_or_compute(
        self, key: str, compute_func: callable, *args, **kwargs
    ) -> NDArray:
        """Get from cache or compute if not present.

        Args:
            key: Cache key
            compute_func: Function to compute data if not cached
            *args: Arguments for compute_func
            **kwargs: Keyword arguments for compute_func

        Returns:
            Cached or computed data
        """
        # Try to get from cache
        data = self.get(key)
        if data is not None:
            return data

        # Compute and cache
        data = compute_func(*args, **kwargs)
        self.put(key, data)

        return data

    def invalidate(self, key: str) -> bool:
        """Remove entry from cache.

        Args:
            key: Cache key

        Returns:
            True if entry was removed
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

        _logger.info("Cache cleared")

    def get_size(self) -> int:
        """Get current cache size in bytes.

        Returns:
            Total size of cached data
        """
        return sum(entry.size_bytes for entry in self._cache.values())

    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_size = self.get_size()

        return {
            "entries": len(self._cache),
            "size_bytes": total_size,
            "size_mb": total_size / 1024 / 1024,
            "utilization": total_size / self.max_size * 100 if self.max_size > 0 else 0,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / (self._hits + self._misses) * 100
            if (self._hits + self._misses) > 0
            else 0,
            "evictions": self._evictions,
        }

    def save_cache(self) -> None:
        """Persist cache to disk."""
        if not self.persist_path:
            return

        try:
            # Create directory if needed
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)

            # Save cache data
            cache_data = {
                "cache": dict(self._cache),
                "statistics": {
                    "hits": self._hits,
                    "misses": self._misses,
                    "evictions": self._evictions,
                },
            }

            with open(self.persist_path, "wb") as f:
                pickle.dump(cache_data, f)

            _logger.info("Cache saved to %s", self.persist_path)

        except Exception as e:
            _logger.error("Failed to save cache: %s", e)

    def _load_cache(self) -> None:
        """Load cache from disk."""
        try:
            with open(self.persist_path, "rb") as f:
                cache_data = pickle.load(f)

            # Restore cache
            self._cache = OrderedDict(cache_data["cache"])

            # Restore statistics
            stats = cache_data.get("statistics", {})
            self._hits = stats.get("hits", 0)
            self._misses = stats.get("misses", 0)
            self._evictions = stats.get("evictions", 0)

            _logger.info(
                "Cache loaded from %s (%d entries)", self.persist_path, len(self._cache)
            )

        except Exception as e:
            _logger.error("Failed to load cache: %s", e)

    def _evict_one(self) -> bool:
        """Evict one entry from cache.

        Returns:
            True if an entry was evicted
        """
        if not self._cache:
            return False

        # Find entry to evict based on policy
        for key in list(self._cache.keys()):
            if self.policy.should_evict(self, key):
                del self._cache[key]
                self._evictions += 1
                _logger.debug("Evicted %s from cache", key)
                return True

        # If policy didn't select anything, evict oldest (FIFO)
        key = next(iter(self._cache))
        del self._cache[key]
        self._evictions += 1
        _logger.debug("Evicted %s from cache (FIFO fallback)", key)
        return True


class MultiLevelCache:
    """Multi-level cache with memory and disk tiers."""

    def __init__(
        self,
        memory_size: int = 512 * 1024 * 1024,  # 512MB memory
        disk_size: int = 10 * 1024 * 1024 * 1024,  # 10GB disk
        cache_dir: Optional[Path] = None,
    ):
        """Initialize multi-level cache.

        Args:
            memory_size: Size of memory cache
            disk_size: Size of disk cache
            cache_dir: Directory for disk cache
        """
        self.memory_cache = RawDataCache(max_size=memory_size, policy=LRUPolicy())

        # Setup disk cache directory
        if cache_dir is None:
            cache_dir = Path.home() / ".cespy" / "cache"
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.disk_size = disk_size
        self._disk_usage = 0
        self._disk_index: Dict[str, Path] = {}

        # Load disk index
        self._load_disk_index()

        _logger.info(
            "MultiLevelCache initialized: %d MB memory, %d GB disk",
            memory_size / 1024 / 1024,
            disk_size / 1024 / 1024 / 1024,
        )

    def get(self, key: str) -> Optional[NDArray]:
        """Get data from cache (checks memory then disk).

        Args:
            key: Cache key

        Returns:
            Cached data or None
        """
        # Check memory cache first
        data = self.memory_cache.get(key)
        if data is not None:
            return data

        # Check disk cache
        if key in self._disk_index:
            try:
                disk_path = self._disk_index[key]
                data = np.load(disk_path)

                # Promote to memory cache
                self.memory_cache.put(key, data)

                return data
            except Exception as e:
                _logger.error("Failed to load from disk cache: %s", e)
                # Remove corrupted entry
                del self._disk_index[key]

        return None

    def put(self, key: str, data: NDArray) -> None:
        """Put data into cache.

        Args:
            key: Cache key
            data: Data to cache
        """
        # Always put in memory cache
        self.memory_cache.put(key, data)

        # Also put in disk cache if it fits
        data_size = data.nbytes
        if data_size <= self.disk_size - self._disk_usage:
            self._save_to_disk(key, data)

    def _save_to_disk(self, key: str, data: NDArray) -> None:
        """Save data to disk cache.

        Args:
            key: Cache key
            data: Data to save
        """
        try:
            # Generate filename
            safe_key = key.replace("/", "_").replace("\\", "_")
            disk_path = self.cache_dir / f"{safe_key}.npy"

            # Save data
            np.save(disk_path, data)

            # Update index
            self._disk_index[key] = disk_path
            self._disk_usage += data.nbytes

            # Save index
            self._save_disk_index()

        except Exception as e:
            _logger.error("Failed to save to disk cache: %s", e)

    def _load_disk_index(self) -> None:
        """Load disk cache index."""
        index_path = self.cache_dir / "index.pkl"
        if index_path.exists():
            try:
                with open(index_path, "rb") as f:
                    self._disk_index = pickle.load(f)

                # Calculate disk usage
                self._disk_usage = 0
                for path in self._disk_index.values():
                    if path.exists():
                        self._disk_usage += path.stat().st_size

            except Exception as e:
                _logger.error("Failed to load disk index: %s", e)
                self._disk_index = {}

    def _save_disk_index(self) -> None:
        """Save disk cache index."""
        try:
            index_path = self.cache_dir / "index.pkl"
            with open(index_path, "wb") as f:
                pickle.dump(self._disk_index, f)
        except Exception as e:
            _logger.error("Failed to save disk index: %s", e)

    def clear(self) -> None:
        """Clear all caches."""
        # Clear memory cache
        self.memory_cache.clear()

        # Clear disk cache
        for path in self._disk_index.values():
            try:
                path.unlink()
            except:
                pass

        self._disk_index.clear()
        self._disk_usage = 0
        self._save_disk_index()

        _logger.info("All caches cleared")
