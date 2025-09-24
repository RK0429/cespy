"""Integration tests for simulator execution across different SPICE engines."""

import shutil
from pathlib import Path

import pytest

from cespy.log.ltsteps import LTSpiceLogReader
from cespy.raw.raw_read import RawRead
from cespy.sim import SimRunner
from cespy.simulators import LTspice, NGspice, Qspice, Xyce


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

        # Run simulation
        runner = SimRunner(simulator=LTspice)
        task = runner.run(netlist_path)
        assert task is not None, "Simulation task should not be None"

        # Wait for completion
        success = runner.wait_completion()
        assert success

        # Get results from task
        raw_file = task.raw_file
        log_file = task.log_file
        assert raw_file is not None
        assert log_file is not None

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
        time_axis = raw_data.get_axis()
        assert hasattr(time_axis, 'data')
        assert time_axis.data[-1] >= 2e-3  # Should simulate to at least 2ms

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
        runner = SimRunner(simulator=LTspice)
        task = runner.run(netlist_path)
        assert task is not None
        success = runner.wait_completion()
        assert success

        # Get results from task
        raw_file = task.raw_file
        log_file = task.log_file
        assert raw_file is not None
        assert log_file is not None

        # Parse results
        raw_data = RawRead(raw_file)

        # AC analysis should have frequency as x-axis
        axis = raw_data.get_axis()
        assert hasattr(axis, 'name')
        assert axis.name == "frequency"

        # Check frequency range
        assert hasattr(axis, 'data')
        assert axis.data[0] >= 1  # Start at 1Hz
        assert axis.data[-1] <= 1e5  # End at 100kHz

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
        runner = SimRunner(simulator=LTspice)
        task = runner.run(netlist_path)
        assert task is not None
        success = runner.wait_completion()
        assert success

        # Get results from task
        raw_file = task.raw_file
        log_file = task.log_file
        assert raw_file is not None
        assert log_file is not None

        # Parse results
        raw_data = RawRead(raw_file)

        # DC sweep should have V1 as x-axis
        axis = raw_data.get_axis()
        assert hasattr(axis, 'name')
        assert axis.name in ["V1", "v1", "v-sweep"]

        # Check voltage range
        assert hasattr(axis, 'data')
        assert axis.data[0] == 0  # Start at 0V
        assert axis.data[-1] == 5  # End at 5V

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
        runner = SimRunner(simulator=LTspice)
        task = runner.run(netlist_path)
        assert task is not None
        success = runner.wait_completion()
        assert success

        # Get results from task
        raw_file = task.raw_file
        log_file = task.log_file
        assert raw_file is not None
        assert log_file is not None

        # Parse log file for steps
        log_reader = LTSpiceLogReader(str(log_file))

        # Check step info from stepset property
        assert hasattr(log_reader, 'stepset')
        if log_reader.stepset:
            # Should have parameter 'Rval' with 5 values
            assert 'rval' in log_reader.stepset  # Note: keys are lowercase
            assert len(log_reader.stepset['rval']) == 5


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

        # Run simulation
        runner = SimRunner(simulator=NGspice)
        task = runner.run(netlist_path)
        assert task is not None
        success = runner.wait_completion()
        assert success

        # Get results from task
        raw_file = task.raw_file
        log_file = task.log_file
        assert raw_file is not None
        assert log_file is not None

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
        runner = SimRunner(simulator=NGspice)
        task = runner.run(netlist_path)
        assert task is not None
        success = runner.wait_completion()
        assert success

        # Get results from task
        raw_file = task.raw_file
        log_file = task.log_file
        assert raw_file is not None
        assert log_file is not None

        # Parse results
        raw_data = RawRead(raw_file)

        # Verify time domain data
        time_axis = raw_data.get_axis()
        assert hasattr(time_axis, 'name')
        assert time_axis.name == "time"
        assert hasattr(time_axis, 'data')
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

        # Run simulation
        runner = SimRunner(simulator=Qspice)
        task = runner.run(netlist_path)
        assert task is not None
        success = runner.wait_completion()
        assert success

        # Get results from task
        raw_file = task.raw_file
        log_file = task.log_file
        assert raw_file is not None
        assert log_file is not None

        # Verify output - Qspice uses .qraw extension
        assert Path(raw_file).exists()
        assert str(raw_file).endswith(".qraw")

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

        # Run simulation
        runner = SimRunner(simulator=Xyce)
        task = runner.run(netlist_path)
        assert task is not None
        success = runner.wait_completion()
        assert success

        # Get results from task
        raw_file = task.raw_file
        log_file = task.log_file
        assert raw_file is not None
        assert log_file is not None

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
    def test_simulation_with_callback(
        self, temp_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
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

        # Define callback to capture results
        results = []

        def capture_results(raw_file: Path, log_file: Path) -> None:
            """Capture simulation results.

            Args:
                raw_file: Path to raw data file
                log_file: Path to log file
            """
            results.append((raw_file, log_file))

        # Run simulation with callback
        runner = SimRunner(simulator=LTspice)
        task = runner.run(netlist_path, callback=capture_results)
        assert task is not None
        success = runner.wait_completion()
        assert success

        # Should have captured results
        assert len(results) > 0

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
        runner = SimRunner(simulator=LTspice, parallel_sims=3)

        # Start all simulations
        tasks = []
        for netlist in netlists:
            task = runner.run(netlist)
            assert task is not None
            tasks.append(task)

        # Wait for all to complete
        success = runner.wait_completion()
        assert success

        # Verify all completed
        assert len(tasks) == 3
        for task in tasks:
            assert task.raw_file is not None
            assert task.log_file is not None
            assert Path(task.raw_file).exists()
            assert Path(task.log_file).exists()
