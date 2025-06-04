"""Integration tests for simulator execution across different SPICE engines."""

import pytest
from pathlib import Path
import shutil
from cespy.simulators import LTspice, NGspice, Qspice, Xyce
from cespy.sim import SimRunner
from cespy.raw.raw_read import RawRead
from cespy.log.ltsteps import LTSpiceLogReader


class TestLTSpiceExecution:
    """Test LTSpice simulator execution."""

    @pytest.mark.requires_ltspice
    def test_ltspice_transient_analysis(self, temp_dir: Path) -> None:
        """Test LTSpice transient analysis execution."""
        # Copy test netlist
        test_netlist = Path(__file__).parent.parent / "testfiles" / "TRAN.net"
        if test_netlist.exists():
            netlist_path = temp_dir / "tran_test.net"
            shutil.copy(test_netlist, netlist_path)
        else:
            # Create a simple test netlist
            netlist_path = temp_dir / "tran_test.net"
            netlist_content = """* Transient Test
V1 in 0 PULSE(0 5 0 1n 1n 0.5m 1m)
R1 in out 1k
C1 out 0 1u
.tran 0 2m 0 1u
.end
"""
            netlist_path.write_text(netlist_content)

        # Create simulator instance
        simulator = LTspice()

        # Run simulation
        runner = SimRunner()
        runner.run(simulator, netlist_path)

        # Wait for completion
        raw_file, log_file = runner.wait_completion()

        # Verify output files
        assert Path(raw_file).exists()
        assert Path(log_file).exists()

        # Parse raw file
        raw_data = RawRead(raw_file)

        # Verify data
        assert raw_data.get_trace("time") is not None
        assert raw_data.get_trace("V(in)") is not None
        assert raw_data.get_trace("V(out)") is not None

        # Check time range
        time_data = raw_data.get_axis().data
        assert time_data[-1] >= 2e-3  # Should simulate to at least 2ms

    @pytest.mark.requires_ltspice
    def test_ltspice_ac_analysis(self, temp_dir: Path) -> None:
        """Test LTSpice AC analysis execution."""
        test_netlist = Path(__file__).parent.parent / "testfiles" / "AC.net"
        if test_netlist.exists():
            netlist_path = temp_dir / "ac_test.net"
            shutil.copy(test_netlist, netlist_path)
        else:
            netlist_path = temp_dir / "ac_test.net"
            netlist_content = """* AC Analysis Test
V1 in 0 AC 1
R1 in out 1k
C1 out 0 1u
.ac dec 10 1 100k
.end
"""
            netlist_path.write_text(netlist_content)

        # Run simulation
        simulator = LTspice()
        runner = SimRunner()
        runner.run(simulator, netlist_path)
        raw_file, log_file = runner.wait_completion()

        # Parse results
        raw_data = RawRead(raw_file)

        # AC analysis should have frequency as x-axis
        axis = raw_data.get_axis()
        assert axis.name == "frequency"

        # Check frequency range
        freq_data = axis.data
        assert freq_data[0] >= 1  # Start at 1Hz
        assert freq_data[-1] <= 1e5  # End at 100kHz

    @pytest.mark.requires_ltspice
    def test_ltspice_dc_sweep(self, temp_dir: Path) -> None:
        """Test LTSpice DC sweep analysis."""
        test_netlist = Path(__file__).parent.parent / "testfiles" / "DC sweep.net"
        if test_netlist.exists():
            netlist_path = temp_dir / "dc_sweep_test.net"
            shutil.copy(test_netlist, netlist_path)
        else:
            netlist_path = temp_dir / "dc_sweep_test.net"
            netlist_content = """* DC Sweep Test
V1 in 0 DC 1
R1 in out 1k
R2 out 0 1k
.dc V1 0 5 0.1
.end
"""
            netlist_path.write_text(netlist_content)

        # Run simulation
        simulator = LTspice()
        runner = SimRunner()
        runner.run(simulator, netlist_path)
        raw_file, log_file = runner.wait_completion()

        # Parse results
        raw_data = RawRead(raw_file)

        # DC sweep should have V1 as x-axis
        axis = raw_data.get_axis()
        assert axis.name in ["V1", "v1", "v-sweep"]

        # Check voltage range
        v_data = axis.data
        assert v_data[0] == 0  # Start at 0V
        assert v_data[-1] == 5  # End at 5V

    @pytest.mark.requires_ltspice
    def test_ltspice_parameter_stepping(self, temp_dir: Path) -> None:
        """Test LTSpice with parameter stepping."""
        netlist_path = temp_dir / "step_test.net"
        netlist_content = """* Parameter Stepping Test
.param Rval=1k
V1 in 0 1
R1 in out {Rval}
C1 out 0 1u
.dc V1 0 1 0.1
.step param Rval 1k 5k 1k
.end
"""
        netlist_path.write_text(netlist_content)

        # Run simulation
        simulator = LTspice()
        runner = SimRunner()
        runner.run(simulator, netlist_path)
        raw_file, log_file = runner.wait_completion()

        # Parse log file for steps
        log_reader = LTSpiceLogReader(log_file)
        steps = log_reader.get_steps()

        # Should have 5 steps (1k, 2k, 3k, 4k, 5k)
        assert len(steps) == 5


class TestNGSpiceExecution:
    """Test NGSpice simulator execution."""

    @pytest.mark.requires_ngspice
    def test_ngspice_basic_simulation(self, temp_dir: Path) -> None:
        """Test basic NGSpice simulation."""
        test_netlist = (
            Path(__file__).parent.parent / "testfiles" / "testfile_ngspice.net"
        )
        if test_netlist.exists():
            netlist_path = temp_dir / "ngspice_test.net"
            shutil.copy(test_netlist, netlist_path)
        else:
            netlist_path = temp_dir / "ngspice_test.net"
            netlist_content = """NGSpice Test Circuit
V1 in 0 DC 1 AC 1
R1 in out 1k
C1 out 0 1u
.ac dec 10 1 10k
.control
run
write ngspice_test.raw
.endc
.end
"""
            netlist_path.write_text(netlist_content)

        # Create simulator instance
        simulator = NGspice()

        # Run simulation
        runner = SimRunner()
        runner.run(simulator, netlist_path)
        raw_file, log_file = runner.wait_completion()

        # Verify output
        assert Path(raw_file).exists()

        # Parse results with NGSpice dialect
        raw_data = RawRead(raw_file)

        # Check traces
        trace_names = raw_data.get_trace_names()
        assert "frequency" in trace_names

    @pytest.mark.requires_ngspice
    def test_ngspice_transient_analysis(self, temp_dir: Path) -> None:
        """Test NGSpice transient analysis."""
        netlist_path = temp_dir / "ngspice_tran.net"
        netlist_content = """NGSpice Transient Test
V1 in 0 PULSE(0 1 0 1n 1n 0.5m 1m)
R1 in out 1k
C1 out 0 1u
.tran 1u 2m
.control
run
write ngspice_tran.raw
.endc
.end
"""
        netlist_path.write_text(netlist_content)

        # Run simulation
        simulator = NGspice()
        runner = SimRunner()
        runner.run(simulator, netlist_path)
        raw_file, log_file = runner.wait_completion()

        # Parse results
        raw_data = RawRead(raw_file)

        # Verify time domain data
        time_axis = raw_data.get_axis()
        assert time_axis.name == "time"
        assert time_axis.data[-1] >= 2e-3


class TestQspiceExecution:
    """Test Qspice simulator execution."""

    @pytest.mark.requires_qspice
    def test_qspice_basic_simulation(self, temp_dir: Path) -> None:
        """Test basic Qspice simulation."""
        # Find a Qspice test netlist
        test_netlist = (
            Path(__file__).parent.parent / "testfiles" / "QSPICE_TRAN - STEP.net"
        )
        if test_netlist.exists():
            netlist_path = temp_dir / "qspice_test.net"
            shutil.copy(test_netlist, netlist_path)
        else:
            netlist_path = temp_dir / "qspice_test.net"
            netlist_content = """* Qspice Test Circuit
V1 in 0 1
R1 in out 1k
C1 out 0 1u
.tran 1m
.end
"""
            netlist_path.write_text(netlist_content)

        # Create simulator instance
        simulator = Qspice()

        # Run simulation
        runner = SimRunner()
        runner.run(simulator, netlist_path)
        raw_file, log_file = runner.wait_completion()

        # Verify output - Qspice uses .qraw extension
        assert Path(raw_file).exists()
        assert raw_file.endswith(".qraw")

        # Parse results
        raw_data = RawRead(raw_file)

        # Check basic functionality
        assert raw_data.get_trace_names() is not None


class TestXyceExecution:
    """Test Xyce simulator execution."""

    @pytest.mark.requires_xyce
    def test_xyce_basic_simulation(self, temp_dir: Path) -> None:
        """Test basic Xyce simulation."""
        netlist_path = temp_dir / "xyce_test.net"
        netlist_content = """* Xyce Test Circuit
V1 in 0 SIN(0 1 1k)
R1 in out 1k
C1 out 0 1u
.tran 0 2m
.print tran V(in) V(out)
.end
"""
        netlist_path.write_text(netlist_content)

        # Create simulator instance
        simulator = Xyce()

        # Run simulation
        runner = SimRunner()
        runner.run(simulator, netlist_path)
        raw_file, log_file = runner.wait_completion()

        # Verify output
        assert Path(raw_file).exists()

        # Parse results
        raw_data = RawRead(raw_file)

        # Check traces
        trace_names = raw_data.get_trace_names()
        assert len(trace_names) > 0


class TestSimulatorWithCallbacks:
    """Test simulator execution with callbacks."""

    @pytest.mark.requires_ltspice
    def test_simulation_with_callback(self, temp_dir: Path, capsys) -> None:
        """Test simulation with process callback."""
        netlist_path = temp_dir / "callback_test.net"
        netlist_content = """* Callback Test
V1 in 0 1
R1 in out 1k
C1 out 0 1u
.tran 1m
.end
"""
        netlist_path.write_text(netlist_content)

        # Define callback to capture output
        output_lines = []

        def capture_output(line):
            output_lines.append(line)

        # Run simulation with callback
        simulator = LTspice()
        runner = SimRunner()
        runner.run(simulator, netlist_path, callback=capture_output)
        runner.wait_completion()

        # Should have captured some output
        assert len(output_lines) > 0

    @pytest.mark.requires_ltspice
    def test_multiple_simulations_parallel(self, temp_dir: Path) -> None:
        """Test running multiple simulations in parallel."""
        # Create multiple netlists
        netlists = []
        for i in range(3):
            netlist_path = temp_dir / f"parallel_test_{i}.net"
            netlist_content = f"""* Parallel Test {i}
V1 in 0 {i+1}
R1 in out {(i+1)*1000}
C1 out 0 1u
.op
.end
"""
            netlist_path.write_text(netlist_content)
            netlists.append(netlist_path)

        # Run simulations in parallel
        simulator = LTspice()
        runner = SimRunner(max_parallel_runs=3)

        # Start all simulations
        for netlist in netlists:
            runner.run(simulator, netlist)

        # Wait for all to complete
        results = []
        for _ in range(3):
            raw_file, log_file = runner.wait_completion()
            results.append((raw_file, log_file))

        # Verify all completed
        assert len(results) == 3
        for raw_file, log_file in results:
            assert Path(raw_file).exists()
            assert Path(log_file).exists()
