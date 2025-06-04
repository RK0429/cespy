"""Performance tests to ensure no regression in execution speed."""

import pytest
import time
from pathlib import Path
import numpy as np
from cespy.raw import RawRead, RawWrite, Trace
from cespy.editor import SpiceEditor
from cespy.simulators import LTspice
from cespy.sim import SimRunner
import psutil
import os


class TestRawFilePerformance:
    """Test performance of raw file operations."""

    def test_large_raw_file_write(self, temp_dir: Path):
        """Test writing large raw files."""
        # Create large dataset (1M points, 10 traces)
        num_points = 1_000_000
        num_traces = 10

        # Measure memory before
        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss / 1024 / 1024  # MB

        # Generate data
        time_data = np.linspace(0, 1, num_points)
        traces = [Trace("time", "time", data=time_data)]

        for i in range(num_traces - 1):
            data = np.sin(2 * np.pi * (i + 1) * time_data) + np.random.normal(0, 0.1, num_points)
            traces.append(Trace(f"V{i+1}", "voltage", data=data))

        # Time the write operation
        raw_file = temp_dir / "large_test.raw"
        start_time = time.time()

        writer = RawWrite(raw_file, "Performance Test", 1e-9)
        for trace in traces:
            writer.add_trace(trace)
        writer.write()

        write_time = time.time() - start_time

        # Check file size
        file_size_mb = raw_file.stat().st_size / 1024 / 1024

        # Performance assertions
        assert write_time < 10.0  # Should write in less than 10 seconds
        assert file_size_mb > 50  # Should be a substantial file

        # Memory usage check
        mem_after = process.memory_info().rss / 1024 / 1024
        mem_increase = mem_after - mem_before
        assert mem_increase < 1000  # Should not use more than 1GB additional memory

        print(f"Write time: {write_time:.2f}s, File size: {file_size_mb:.1f}MB, Memory increase: {mem_increase:.1f}MB")

    def test_large_raw_file_read(self, temp_dir: Path):
        """Test reading large raw files."""
        # First create a large file
        num_points = 500_000
        time_data = np.linspace(0, 1, num_points)
        traces = [
            Trace("time", "time", data=time_data),
            Trace("V1", "voltage", data=np.sin(2 * np.pi * time_data)),
            Trace("V2", "voltage", data=np.cos(2 * np.pi * time_data)),
            Trace("I1", "current", data=np.sin(4 * np.pi * time_data) * 0.001)
        ]

        raw_file = temp_dir / "read_test.raw"
        writer = RawWrite(raw_file, "Read Test", 1e-9)
        for trace in traces:
            writer.add_trace(trace)
        writer.write()

        # Time the read operation
        start_time = time.time()
        reader = RawRead(raw_file)

        # Read all traces
        for trace_name in reader.get_trace_names():
            data = reader.get_trace(trace_name).data
            assert len(data) == num_points

        read_time = time.time() - start_time

        # Performance assertion
        assert read_time < 5.0  # Should read in less than 5 seconds
        print(f"Read time for {num_points} points: {read_time:.2f}s")

    def test_stepped_data_performance(self, temp_dir: Path):
        """Test performance with stepped parameter data."""
        # Create stepped data (100 steps, 10k points each)
        num_steps = 100
        points_per_step = 10_000

        all_time = []
        all_voltage = []

        for step in range(num_steps):
            time = np.linspace(0, 1e-3, points_per_step)
            voltage = (step + 1) * np.sin(2 * np.pi * 1000 * time)
            all_time.extend(time)
            all_voltage.extend(voltage)

        traces = [
            Trace("time", "time", data=np.array(all_time)),
            Trace("V(out)", "voltage", data=np.array(all_voltage))
        ]

        raw_file = temp_dir / "stepped_test.raw"

        # Time write with stepped data
        start_time = time.time()
        writer = RawWrite(raw_file, "Stepped Test", 1e-9)
        writer.set_no_steps(num_steps)
        writer.set_no_points(points_per_step)
        for trace in traces:
            writer.add_trace(trace)
        writer.write()
        write_time = time.time() - start_time

        # Time read with step access
        start_time = time.time()
        reader = RawRead(raw_file)

        # Access data from different steps
        for step in [0, 25, 50, 75, 99]:
            data = reader.get_trace("V(out)", step=step).data
            assert len(data) == points_per_step

        read_time = time.time() - start_time

        # Performance assertions
        assert write_time < 5.0
        assert read_time < 2.0
        print(f"Stepped data - Write: {write_time:.2f}s, Read: {read_time:.2f}s")


class TestEditorPerformance:
    """Test performance of netlist editing operations."""

    def test_large_netlist_editing(self, temp_dir: Path):
        """Test editing performance with large netlists."""
        # Create a large netlist (10k components)
        netlist_path = temp_dir / "large_netlist.net"

        lines = ["* Large Netlist Test\n"]
        lines.append("V1 vdd 0 5\n")

        # Add many resistors
        for i in range(5000):
            lines.append(f"R{i} n{i} n{i+1} 1k\n")

        # Add many capacitors
        for i in range(5000):
            lines.append(f"C{i} n{i+5000} 0 1n\n")

        lines.append(".op\n")
        lines.append(".end\n")

        netlist_path.write_text("".join(lines))

        # Time the loading
        start_time = time.time()
        editor = SpiceEditor(netlist_path)
        load_time = time.time() - start_time

        # Time component access
        start_time = time.time()
        components = editor.get_components()
        assert len(components) == 10001  # 10k + V1
        access_time = time.time() - start_time

        # Time component value changes
        start_time = time.time()
        for i in range(100):
            editor.set_component_value(f"R{i}", f"{(i+1)*100}")
        change_time = time.time() - start_time

        # Time save operation
        start_time = time.time()
        editor.save_netlist()
        save_time = time.time() - start_time

        # Performance assertions
        assert load_time < 1.0  # Should load in less than 1 second
        assert access_time < 0.5  # Component access should be fast
        assert change_time < 0.5  # 100 changes should be quick
        assert save_time < 1.0  # Save should be fast

        print(f"Large netlist - Load: {load_time:.3f}s, Access: {access_time:.3f}s, Change: {change_time:.3f}s, Save: {save_time:.3f}s")

    def test_parameter_search_performance(self, temp_dir: Path):
        """Test performance of parameter searches in large netlists."""
        # Create netlist with many parameters
        netlist_path = temp_dir / "param_test.net"

        lines = ["* Parameter Test\n"]

        # Add many parameters
        for i in range(1000):
            lines.append(f".param p{i}={i}\n")

        lines.append("V1 in 0 1\n")
        lines.append("R1 in out {p1*p2}\n")
        lines.append(".op\n")
        lines.append(".end\n")

        netlist_path.write_text("".join(lines))

        # Load netlist
        editor = SpiceEditor(netlist_path)

        # Time parameter access
        start_time = time.time()
        for i in range(0, 1000, 10):  # Check every 10th parameter
            value = editor.get_parameter(f"p{i}")
            assert value == str(i)
        access_time = time.time() - start_time

        # Time parameter updates
        start_time = time.time()
        for i in range(0, 100):
            editor.set_parameter(f"p{i}", str(i * 2))
        update_time = time.time() - start_time

        # Performance assertions
        assert access_time < 0.5  # 100 accesses should be fast
        assert update_time < 0.5  # 100 updates should be fast

        print(f"Parameter operations - Access: {access_time:.3f}s, Update: {update_time:.3f}s")


class TestSimulationPerformance:
    """Test simulation execution performance."""

    @pytest.mark.requires_ltspice
    def test_parallel_simulation_performance(self, temp_dir: Path):
        """Test performance of parallel simulations."""
        # Create multiple simple netlists
        netlists = []
        for i in range(10):
            netlist_path = temp_dir / f"parallel_{i}.net"
            content = f"""* Parallel Test {i}
V1 in 0 PULSE(0 {i+1} 0 1n 1n 0.5m 1m)
R1 in out {(i+1)*1000}
C1 out 0 1u
.tran 0 2m 0 10u
.end
"""
            netlist_path.write_text(content)
            netlists.append(netlist_path)

        simulator = LTspice()

        # Test sequential execution
        runner_seq = SimRunner(max_parallel_runs=1)
        start_time = time.time()

        for netlist in netlists:
            runner_seq.run(simulator, netlist)

        # Wait for all to complete
        for _ in range(10):
            runner_seq.wait_completion()

        seq_time = time.time() - start_time

        # Test parallel execution
        runner_par = SimRunner(max_parallel_runs=4)
        start_time = time.time()

        for netlist in netlists:
            runner_par.run(simulator, netlist)

        # Wait for all to complete
        for _ in range(10):
            runner_par.wait_completion()

        par_time = time.time() - start_time

        # Parallel should be faster
        speedup = seq_time / par_time
        assert speedup > 1.5  # At least 1.5x speedup with 4 parallel runs

        print(f"Sequential: {seq_time:.2f}s, Parallel: {par_time:.2f}s, Speedup: {speedup:.2f}x")

    @pytest.mark.requires_ltspice
    def test_simulation_timeout_performance(self, temp_dir: Path):
        """Test that simulation timeouts work correctly."""
        # Create a netlist that would run for a long time
        netlist_path = temp_dir / "timeout_test.net"
        content = """* Timeout Test
V1 in 0 PULSE(0 1 0 1n 1n 0.5m 1m)
R1 in out 1k
C1 out 0 1u
.tran 0 100 0 1u
.end
"""
        netlist_path.write_text(content)

        simulator = LTspice()
        runner = SimRunner()
        runner.set_simulation_timeout(2)  # 2 second timeout

        start_time = time.time()
        runner.run(simulator, netlist_path)

        # Should timeout
        with pytest.raises(Exception):  # Timeout exception
            runner.wait_completion()

        elapsed = time.time() - start_time
        assert elapsed < 3  # Should timeout within 3 seconds

        print(f"Timeout test completed in {elapsed:.2f}s")


class TestMemoryUsage:
    """Test memory usage to detect leaks."""

    def test_repeated_operations_memory(self, temp_dir: Path):
        """Test that repeated operations don't leak memory."""
        process = psutil.Process(os.getpid())

        # Create test netlist
        netlist_path = temp_dir / "memory_test.net"
        content = """* Memory Test
V1 in 0 1
R1 in out 1k
C1 out 0 1u
.tran 1m
.end
"""
        netlist_path.write_text(content)

        # Get baseline memory
        mem_baseline = process.memory_info().rss / 1024 / 1024

        # Perform many operations
        for i in range(100):
            # Load and edit netlist
            editor = SpiceEditor(netlist_path)
            editor.set_component_value("R1", f"{i+1}k")
            editor.set_parameter("test_param", str(i))
            editor.save_netlist()

            # Create and write raw file
            raw_file = temp_dir / f"test_{i}.raw"
            writer = RawWrite(raw_file, "Test", 1e-6)
            writer.add_trace(Trace("time", "time", data=np.linspace(0, 1, 1000)))
            writer.add_trace(Trace("V1", "voltage", data=np.random.rand(1000)))
            writer.write()

            # Read raw file
            reader = RawRead(raw_file)
            _ = reader.get_trace("V1").data

            # Clean up file
            raw_file.unlink()

        # Check memory after operations
        mem_after = process.memory_info().rss / 1024 / 1024
        mem_increase = mem_after - mem_baseline

        # Should not have significant memory increase
        assert mem_increase < 100  # Less than 100MB increase

        print(f"Memory usage - Baseline: {mem_baseline:.1f}MB, After: {mem_after:.1f}MB, Increase: {mem_increase:.1f}MB")
