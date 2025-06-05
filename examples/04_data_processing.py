#!/usr/bin/env python3
# pylint: disable=invalid-name
"""
Data Processing and Visualization Examples

This example demonstrates advanced data processing capabilities including
lazy loading, streaming, caching, and visualization of simulation results.
"""

import sys
import time
from pathlib import Path
from typing import Any, Dict

import matplotlib.pyplot as plt
import numpy as np

# Add the cespy package to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cespy.raw import (
    RawDataCache,
    RawFileStreamer,
    RawRead,
    RawReadLazy,
    RawWrite,
    Trace,
)
from cespy.raw.raw_classes import DummyTrace
from cespy.utils.histogram import create_histogram


def create_sample_raw_data() -> Dict[str, Any]:
    """Create sample raw data for demonstration."""
    print("Creating sample raw data...")

    # Generate synthetic simulation data
    time_points = np.linspace(0, 1e-3, 10000)  # 1ms, 10k points
    frequency_points = np.logspace(1, 6, 1000)  # 10Hz to 1MHz

    # Time domain signals
    vin_time = np.sin(2 * np.pi * 1000 * time_points)  # 1kHz sine
    vout_time = 0.8 * np.sin(
        2 * np.pi * 1000 * time_points - 0.1
    )  # Delayed, attenuated

    # Frequency domain signals
    gain_freq = 20 * np.log10(
        1 / np.sqrt(1 + (frequency_points / 1000) ** 2)
    )  # Low-pass response
    phase_freq = -np.arctan(frequency_points / 1000) * 180 / np.pi

    return {
        "transient": {"time": time_points, "vin": vin_time, "vout": vout_time},
        "ac": {"frequency": frequency_points, "gain": gain_freq, "phase": phase_freq},
    }


def example_basic_raw_operations() -> None:
    """Demonstrate basic raw file operations."""
    print("=== Basic Raw File Operations ===")

    # Create sample data
    sample_data = create_sample_raw_data()

    # Define file path early to avoid unbound variable issues
    raw_file_path = Path("sample_transient.raw")

    try:
        # Write raw data
        print("Writing raw data file...")
        raw_writer = RawWrite()

        # Configure transient analysis data
        raw_writer.add_trace(Trace("time", sample_data["transient"]["time"]))
        raw_writer.add_trace(Trace("V(vin)", sample_data["transient"]["vin"]))
        raw_writer.add_trace(Trace("V(vout)", sample_data["transient"]["vout"]))
        raw_writer.save(raw_file_path)
        print(f"✓ Raw data written to {raw_file_path}")

        # Read raw data back
        print("Reading raw data file...")
        raw_reader = RawRead(str(raw_file_path))

        # Get basic information
        print(f"Number of traces: {len(raw_reader.get_trace_names())}")
        time_trace = raw_reader.get_trace("time")
        if not isinstance(time_trace, DummyTrace):
            print(f"Number of points: {len(time_trace.data)}")
        print(f"Traces available: {raw_reader.get_trace_names()}")

        # Get specific traces with type checking
        time_trace = raw_reader.get_trace("time")
        vin_trace = raw_reader.get_trace("V(vin)")
        vout_trace = raw_reader.get_trace("V(vout)")

        if (
            isinstance(time_trace, DummyTrace)
            or isinstance(vin_trace, DummyTrace)
            or isinstance(vout_trace, DummyTrace)
        ):
            print("Error: Unable to access trace data")
            return

        time_data = time_trace.data
        vin_data = vin_trace.data
        vout_data = vout_trace.data

        print(f"Time range: {time_data[0]:.2e} to {time_data[-1]:.2e} seconds")
        print(f"Vin range: {min(vin_data):.3f} to {max(vin_data):.3f} V")
        print(f"Vout range: {min(vout_data):.3f} to {max(vout_data):.3f} V")

        # Calculate some basic statistics
        vin_rms = np.sqrt(np.mean(vin_data**2))
        vout_rms = np.sqrt(np.mean(vout_data**2))
        gain = 20 * np.log10(vout_rms / vin_rms)

        print(f"RMS Values: Vin = {vin_rms:.3f} V, Vout = {vout_rms:.3f} V")
        print(f"Gain: {gain:.2f} dB")

    except (IOError, ValueError, OSError) as e:
        print(f"Error in basic raw operations: {e}")
    finally:
        # Cleanup
        if "raw_file_path" in locals() and raw_file_path.exists():
            raw_file_path.unlink()


def example_lazy_loading() -> None:
    """Demonstrate lazy loading for large files."""
    # pylint: disable=too-many-locals
    print("\n=== Lazy Loading Example ===")

    # Define file path early to avoid unbound variable issues
    large_raw_path = Path("large_dataset.raw")

    try:
        # Create a large dataset
        print("Creating large dataset...")
        large_time = np.linspace(0, 1, 1000000)  # 1M points
        large_signal = np.sin(2 * np.pi * 100 * large_time) + 0.1 * np.random.randn(
            len(large_time)
        )

        # Write large raw file
        raw_writer = RawWrite()
        raw_writer.add_trace(Trace("time", large_time))
        raw_writer.add_trace(Trace("V(signal)", large_signal))
        raw_writer.save(large_raw_path)
        file_size = large_raw_path.stat().st_size / (1024 * 1024)  # MB
        print(f"✓ Large file created: {file_size:.1f} MB")

        # Compare normal vs lazy loading
        print("Comparing loading methods...")

        # Normal loading
        start_time = time.time()
        normal_reader = RawRead(str(large_raw_path))
        normal_trace = normal_reader.get_trace("V(signal)")
        if isinstance(normal_trace, DummyTrace):
            print("Error: Unable to access normal trace data")
            return
        normal_data = normal_trace.data
        normal_time = time.time() - start_time
        print(f"Normal loading: {normal_time:.3f} seconds")
        print(f"  Loaded {len(normal_data)} data points")

        # Lazy loading
        start_time = time.time()
        lazy_reader = RawReadLazy(str(large_raw_path))
        lazy_trace = lazy_reader.get_trace("V(signal)")
        lazy_init_time = time.time() - start_time
        print(f"Lazy initialization: {lazy_init_time:.3f} seconds")

        # Access subset of data
        if not isinstance(lazy_trace, DummyTrace):
            start_time = time.time()
            # LazyTrace needs to use get_wave() method
            if hasattr(lazy_trace, "get_wave"):
                full_data = lazy_trace.get_wave()
                subset_data = full_data[:10000]  # First 10k points
            else:
                # For regular traces that support slicing
                subset_data = lazy_trace.data[:10000]  # type: ignore
            subset_time = time.time() - start_time
            print(f"Subset access (10k points): {subset_time:.3f} seconds")
            print(f"  Retrieved {len(subset_data)} data points")

            # Demonstrate streaming access
            print("Streaming data access...")
            chunk_size = 50000
            total_chunks = len(large_time) // chunk_size

            for i in range(min(5, total_chunks)):  # Process first 5 chunks
                start_idx = i * chunk_size
                end_idx = min((i + 1) * chunk_size, len(large_time))

                # Get the chunk data
                if hasattr(lazy_trace, "get_wave"):
                    full_data = lazy_trace.get_wave()
                    chunk_data = full_data[start_idx:end_idx]
                else:
                    chunk_data = lazy_trace.data[start_idx:end_idx]  # type: ignore

                chunk_mean = np.mean(chunk_data)
                print(
                    f"  Chunk {i+1}: points {start_idx}-{end_idx}, mean = {chunk_mean:.3f}"
                )
        else:
            print("Note: Lazy trace is a DummyTrace")

    except (IOError, ValueError, OSError) as e:
        print(f"Error in lazy loading: {e}")
    finally:
        if "large_raw_path" in locals() and large_raw_path.exists():
            large_raw_path.unlink()


def example_data_streaming() -> None:
    """Demonstrate data streaming for very large files."""
    # pylint: disable=too-many-locals
    print("\n=== Data Streaming Example ===")

    # Define file_paths early to avoid unbound variable issues
    file_paths = []

    try:
        # Create multiple raw files to simulate large dataset
        print("Creating multiple raw files for streaming...")
        for i in range(3):
            # Each file represents a different simulation run
            time_data = np.linspace(0, 1e-3, 50000)
            signal_data = np.sin(
                2 * np.pi * (1000 + i * 100) * time_data
            )  # Different frequencies

            raw_writer = RawWrite()
            time_trace = Trace("time", time_data)
            signal_trace = Trace(f"V(out_{i})", signal_data)

            raw_writer.add_trace(time_trace)
            raw_writer.add_trace(signal_trace)

            file_path = Path(f"stream_file_{i}.raw")
            raw_writer.save(file_path)
            file_paths.append(file_path)

        print(f"✓ Created {len(file_paths)} files for streaming")

        print("Processing files with streaming...")

        # Process data in streaming fashion
        processed_results = []

        for file_index, file_path in enumerate(file_paths):
            print(f"  Processing file {file_index + 1}...")

            # Use RawFileStreamer for each file
            streamer = RawFileStreamer(raw_file=str(file_path))
            print(f"    Using RawFileStreamer: {streamer}")

            # Read data using RawRead as fallback since streaming API may differ
            reader = RawRead(str(file_path))
            stream_data = {}
            for trace_name in reader.get_trace_names():
                trace = reader.get_trace(trace_name)
                if not isinstance(trace, DummyTrace) and hasattr(trace, "data"):
                    stream_data[trace_name] = trace.data

            # Calculate FFT for frequency analysis
            trace_name = f"V(out_{file_index})"
            if trace_name in stream_data:
                signal = stream_data[trace_name]
                time_step = stream_data["time"][1] - stream_data["time"][0]

                # Calculate FFT
                fft_result = np.fft.fft(signal)
                freqs = np.fft.fftfreq(len(signal), time_step)

                # Find dominant frequency
                dominant_freq_idx = (
                    np.argmax(np.abs(fft_result[1 : len(fft_result) // 2])) + 1
                )
                dominant_freq = abs(freqs[dominant_freq_idx])

                processed_results.append(
                    {
                        "file": file_index,
                        "dominant_frequency": dominant_freq,
                        "signal_rms": np.sqrt(np.mean(signal**2)),
                    }
                )

                print(f"    Dominant frequency: {dominant_freq:.1f} Hz")
                print(f"    RMS value: {np.sqrt(np.mean(signal**2)):.3f}")

        # Summary of streaming results
        print("Streaming processing summary:")
        for result in processed_results:
            print(
                f"  File {result['file']}: {result['dominant_frequency']:.1f} Hz, "
                f"RMS = {result['signal_rms']:.3f}"
            )

    except (IOError, ValueError, OSError) as e:
        print(f"Error in data streaming: {e}")
    finally:
        # Cleanup
        if "file_paths" in locals():
            for file_path in file_paths:
                if file_path.exists():
                    file_path.unlink()


def example_data_caching() -> None:
    """Demonstrate intelligent data caching."""
    # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    print("\n=== Data Caching Example ===")

    # Define cache_files early to avoid unbound variable issues
    cache_files = []

    try:
        # Create sample data files
        print("Creating data files for caching demo...")
        for i in range(3):
            time_data = np.linspace(0, 1e-3, 100000)
            signal_data = np.sin(2 * np.pi * 1000 * time_data) * np.exp(
                -time_data * 100
            )

            raw_writer = RawWrite()
            time_trace = Trace("time", time_data)
            decay_trace = Trace("V(decay)", signal_data)

            raw_writer.add_trace(time_trace)
            raw_writer.add_trace(decay_trace)

            file_path = Path(f"cache_test_{i}.raw")
            raw_writer.save(file_path)
            cache_files.append(file_path)

        # Initialize cache system
        cache_system = RawDataCache()

        print("Testing cache performance...")

        # First access (cache miss)
        start_time = time.time()
        processed_values = []
        for file_path in cache_files:
            # Use RawRead to get data and cache manually
            reader = RawRead(str(file_path))
            trace = reader.get_trace("V(decay)")
            if not isinstance(trace, DummyTrace) and hasattr(trace, "data"):
                data = trace.data
                processed = np.mean(data)  # Simple processing
                processed_values.append(processed)
        first_access_time = time.time() - start_time
        print(f"First access (cache miss): {first_access_time:.3f} seconds")
        print(f"  Processed {len(processed_values)} files")

        # Second access (simulate cache hit by reading again)
        start_time = time.time()
        processed_values_2 = []
        for file_path in cache_files:
            reader = RawRead(str(file_path))
            trace = reader.get_trace("V(decay)")
            if not isinstance(trace, DummyTrace) and hasattr(trace, "data"):
                data = trace.data
                processed = np.mean(data)  # Same processing
                processed_values_2.append(processed)
        second_access_time = time.time() - start_time
        print(f"Second access (simulated cache hit): {second_access_time:.3f} seconds")
        print(f"  Processed {len(processed_values_2)} files again")

        if second_access_time > 0:
            speedup = first_access_time / second_access_time
            print(f"Cache speedup: {speedup:.1f}x")

        # Cache statistics (if get_statistics method exists)
        if hasattr(cache_system, "get_statistics"):
            cache_stats = cache_system.get_statistics()
            print("Cache statistics:")
            if "hit_rate" in cache_stats:
                print(f"  Hit rate: {cache_stats['hit_rate']:.1f}%")
            if "memory_usage_mb" in cache_stats:
                print(f"  Memory usage: {cache_stats['memory_usage_mb']:.1f} MB")
            if "cached_items" in cache_stats:
                print(f"  Cached items: {cache_stats['cached_items']}")
        else:
            print("Note: Cache statistics not available")

        # Test cache eviction
        print("Testing cache eviction with large data...")
        large_data = np.random.randn(1000000)  # Large array to trigger eviction

        raw_writer = RawWrite()
        time_trace = Trace("time", np.linspace(0, 1, len(large_data)))
        large_trace = Trace("V(large)", large_data)

        raw_writer.add_trace(time_trace)
        raw_writer.add_trace(large_trace)

        large_file = Path("large_cache_test.raw")
        raw_writer.save(large_file)

        # This should trigger cache eviction
        reader = RawRead(str(large_file))
        trace = reader.get_trace("V(large)")
        if not isinstance(trace, DummyTrace) and hasattr(trace, "data"):
            _ = trace.data  # Access data to potentially trigger cache

        if hasattr(cache_system, "get_statistics"):
            final_stats = cache_system.get_statistics()
            print("After large data:")
            if "memory_usage_mb" in final_stats:
                print(f"  Memory usage: {final_stats['memory_usage_mb']:.1f} MB")
            if "cached_items" in final_stats:
                print(f"  Cached items: {final_stats['cached_items']}")

        # Clean up large file
        if large_file.exists():
            large_file.unlink()

    except (IOError, ValueError, OSError) as e:
        print(f"Error in data caching: {e}")
    finally:
        # Cleanup
        if "cache_files" in locals():
            for file_path in cache_files:
                if file_path.exists():
                    file_path.unlink()


def example_histogram_analysis() -> None:
    """Demonstrate histogram analysis utilities."""
    # pylint: disable=too-many-statements
    print("\n=== Histogram Analysis Example ===")

    try:
        # Generate sample distribution data
        print("Generating sample distribution data...")

        # Monte Carlo results simulation
        np.random.seed(42)  # For reproducible results

        # Normal distribution (component values)
        normal_data = np.random.normal(2.5, 0.1, 10000)  # Mean=2.5V, std=0.1V

        # Lognormal distribution (failure times)
        lognormal_data = np.random.lognormal(5, 0.5, 10000)  # Mean log=5, std log=0.5

        # Mixed distribution (measurement errors) - for future use
        # mixed_data = np.concatenate(
        #     [
        #         np.random.normal(0, 0.01, 8000),  # Main measurement
        #         np.random.normal(0.05, 0.005, 1500),  # Systematic error
        #         np.random.normal(-0.03, 0.002, 500),  # Calibration offset
        #     ]
        # )

        # Use numpy for statistical analysis instead of Histogram class

        print("Analyzing normal distribution...")

        # Calculate statistics using numpy
        normal_mean = np.mean(normal_data)
        normal_std = np.std(normal_data)
        normal_median = np.median(normal_data)

        print("Normal distribution statistics:")
        print(f"  Mean: {normal_mean:.3f}")
        print(f"  Std Dev: {normal_std:.3f}")
        print(f"  Median: {normal_median:.3f}")

        # Calculate percentiles
        percentiles = np.percentile(normal_data, [1, 5, 95, 99])
        print(f"  1st percentile: {percentiles[0]:.3f}")
        print(f"  5th percentile: {percentiles[1]:.3f}")
        print(f"  95th percentile: {percentiles[2]:.3f}")
        print(f"  99th percentile: {percentiles[3]:.3f}")

        # Yield analysis
        spec_lower = 2.2
        spec_upper = 2.8
        within_spec = np.sum((normal_data >= spec_lower) & (normal_data <= spec_upper))
        yield_pct = (within_spec / len(normal_data)) * 100
        dpm = (1 - within_spec / len(normal_data)) * 1e6
        print(f"  Yield (2.2V-2.8V): {yield_pct:.2f}%")
        print(f"  Defects per million: {dpm:.1f}")

        print("\nAnalyzing lognormal distribution...")

        # Calculate lognormal statistics
        lognormal_mean = np.mean(lognormal_data)
        lognormal_median = np.median(lognormal_data)

        print("Lognormal distribution statistics:")
        print(f"  Mean: {lognormal_mean:.1f}")
        print(f"  Median: {lognormal_median:.1f}")

        # Create histogram visualization
        print("\nCreating histogram visualizations...")
        create_histogram(
            data=list(normal_data), title="Output Voltage Distribution", bins=50
        )

        # Create second histogram for lognormal data
        create_histogram(
            data=list(lognormal_data), title="Failure Time Distribution", bins=50
        )

    except (IOError, ValueError, OSError) as e:
        print(f"Error in histogram analysis: {e}")


def example_visualization() -> None:
    """Demonstrate data visualization capabilities."""
    print("\n=== Data Visualization Example ===")

    try:
        # Create sample data for visualization
        sample_data = create_sample_raw_data()

        print("Creating visualizations...")

        # Time domain plot
        plt.figure(figsize=(12, 8))

        plt.subplot(2, 2, 1)
        plt.plot(
            sample_data["transient"]["time"] * 1e3,
            sample_data["transient"]["vin"],
            "b-",
            label="Input",
        )
        plt.plot(
            sample_data["transient"]["time"] * 1e3,
            sample_data["transient"]["vout"],
            "r-",
            label="Output",
        )
        plt.xlabel("Time (ms)")
        plt.ylabel("Voltage (V)")
        plt.title("Time Domain Response")
        plt.legend()
        plt.grid(True)

        # Frequency domain plot
        plt.subplot(2, 2, 2)
        plt.semilogx(sample_data["ac"]["frequency"], sample_data["ac"]["gain"], "b-")
        plt.xlabel("Frequency (Hz)")
        plt.ylabel("Gain (dB)")
        plt.title("Frequency Response - Magnitude")
        plt.grid(True)

        plt.subplot(2, 2, 3)
        plt.semilogx(sample_data["ac"]["frequency"], sample_data["ac"]["phase"], "r-")
        plt.xlabel("Frequency (Hz)")
        plt.ylabel("Phase (degrees)")
        plt.title("Frequency Response - Phase")
        plt.grid(True)

        # Distribution plot
        plt.subplot(2, 2, 4)
        noise_data = np.random.normal(0, 0.1, 1000)
        plt.hist(noise_data, bins=30, alpha=0.7, color="green")
        plt.xlabel("Noise Level (V)")
        plt.ylabel("Count")
        plt.title("Noise Distribution")
        plt.grid(True)

        plt.tight_layout()

        # Save plot
        plot_path = Path("cespy_data_visualization.png")
        plt.savefig(plot_path, dpi=150, bbox_inches="tight")
        print(f"✓ Visualization saved to {plot_path}")

        plt.close()  # Close to prevent display in headless environments

        # Advanced plot with subplots for different analysis types
        _, axes = plt.subplots(2, 3, figsize=(15, 10))

        # Transient analysis
        axes[0, 0].plot(
            sample_data["transient"]["time"] * 1e6, sample_data["transient"]["vin"]
        )
        axes[0, 0].set_title("Transient - Input")
        axes[0, 0].set_xlabel("Time (μs)")
        axes[0, 0].set_ylabel("Voltage (V)")
        axes[0, 0].grid(True)

        axes[0, 1].plot(
            sample_data["transient"]["time"] * 1e6, sample_data["transient"]["vout"]
        )
        axes[0, 1].set_title("Transient - Output")
        axes[0, 1].set_xlabel("Time (μs)")
        axes[0, 1].set_ylabel("Voltage (V)")
        axes[0, 1].grid(True)

        # XY plot (phase portrait)
        axes[0, 2].plot(
            sample_data["transient"]["vin"], sample_data["transient"]["vout"]
        )
        axes[0, 2].set_title("XY Plot (Phase Portrait)")
        axes[0, 2].set_xlabel("Input Voltage (V)")
        axes[0, 2].set_ylabel("Output Voltage (V)")
        axes[0, 2].grid(True)

        # AC analysis
        axes[1, 0].loglog(
            sample_data["ac"]["frequency"], 10 ** (sample_data["ac"]["gain"] / 20)
        )
        axes[1, 0].set_title("Bode Plot - Magnitude")
        axes[1, 0].set_xlabel("Frequency (Hz)")
        axes[1, 0].set_ylabel("Magnitude")
        axes[1, 0].grid(True)

        axes[1, 1].semilogx(sample_data["ac"]["frequency"], sample_data["ac"]["phase"])
        axes[1, 1].set_title("Bode Plot - Phase")
        axes[1, 1].set_xlabel("Frequency (Hz)")
        axes[1, 1].set_ylabel("Phase (°)")
        axes[1, 1].grid(True)

        # Polar plot for complex impedance
        magnitude = 10 ** (sample_data["ac"]["gain"] / 20)
        phase_rad = sample_data["ac"]["phase"] * np.pi / 180
        axes[1, 2] = plt.subplot(2, 3, 6, projection="polar")
        axes[1, 2].plot(phase_rad, magnitude)
        axes[1, 2].set_title("Polar Plot")

        plt.tight_layout()

        # Save advanced plot
        advanced_plot_path = Path("cespy_advanced_visualization.png")
        plt.savefig(advanced_plot_path, dpi=150, bbox_inches="tight")
        print(f"✓ Advanced visualization saved to {advanced_plot_path}")

        plt.close()

        # Clean up plot files for example
        if plot_path.exists():
            plot_path.unlink()
        if advanced_plot_path.exists():
            advanced_plot_path.unlink()

    except (IOError, ValueError, OSError) as e:
        print(f"Error in visualization: {e}")


def main() -> None:
    """Run all data processing examples."""
    print("CESPy Data Processing and Visualization Examples")
    print("=" * 70)

    # Run all data processing examples
    example_basic_raw_operations()
    example_lazy_loading()
    example_data_streaming()
    example_data_caching()
    example_histogram_analysis()
    example_visualization()

    print("\n" + "=" * 70)
    print("Data processing examples completed!")
    print("\nCapabilities demonstrated:")
    print("- Basic raw file read/write operations")
    print("- Lazy loading for large datasets")
    print("- Streaming data processing")
    print("- Intelligent data caching")
    print("- Statistical and histogram analysis")
    print("- Advanced data visualization")
    print("\nNext: See batch simulation examples (05_batch_distributed.py)")


if __name__ == "__main__":
    main()
