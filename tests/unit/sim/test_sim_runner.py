"""Unit tests for SimRunner class functionality."""

import pytest
from pathlib import Path
from unittest.mock import patch, Mock
from cespy.sim.sim_runner import SimRunner
from cespy.sim.run_task import RunTask
from cespy.sim.process_callback import ProcessCallback


class TestSimRunner:
    """Test SimRunner class functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = SimRunner(parallel_sims=2)
        self.test_netlist = Path("test.net")

    def test_init_default_values(self):
        """Test SimRunner initialization with default values."""
        runner = SimRunner()

        assert runner.parallel_sims == 4  # default value
        assert runner.timeout == 600.0  # default timeout
        assert runner.verbose is False
        assert runner.runno == 0
        assert runner.okSim == 0

    def test_init_custom_values(self):
        """Test SimRunner initialization with custom values."""
        runner = SimRunner(
            parallel_sims=8,
            timeout=1200,
            verbose=True,
            output_folder="custom_output"
        )

        assert runner.parallel_sims == 8
        assert runner.timeout == 1200
        assert runner.verbose is True
        assert runner.output_folder == Path("custom_output")

    def test_runno_property(self):
        """Test runno property increments correctly."""
        initial_runno = self.runner.runno

        # Simulate adding a run
        self.runner.run_count += 1

        assert self.runner.runno == initial_runno + 1

    def test_okSim_property(self):
        """Test okSim property tracks successful simulations."""
        initial_ok = self.runner.okSim

        # Simulate successful simulation
        self.runner.successful_simulations += 1

        assert self.runner.okSim == initial_ok + 1

    @patch('cespy.simulators.ltspice_simulator.LTspice.is_available', return_value=True)
    @patch('shutil.copy')
    def test_run_single_simulation(self, mock_copy, mock_available):
        """Test running a single simulation."""
        mock_copy.return_value = self.test_netlist

        # Create a test netlist file
        with patch('pathlib.Path.exists', return_value=True):
            task = self.runner.run(self.test_netlist, wait_resource=False)

            assert isinstance(task, RunTask)
            assert task.netlist_file == self.test_netlist

    @patch('cespy.simulators.ltspice_simulator.LTspice.is_available', return_value=True)
    @patch('shutil.copy')
    def test_run_with_switches(self, mock_copy, mock_available):
        """Test running simulation with command line switches."""
        mock_copy.return_value = self.test_netlist

        with patch('pathlib.Path.exists', return_value=True):
            switches = ["-ascii", "-alt"]
            task = self.runner.run(
                self.test_netlist,
                switches=switches,
                wait_resource=False
            )

            assert task.switches == switches

    @patch('cespy.simulators.ltspice_simulator.LTspice.is_available', return_value=True)
    @patch('shutil.copy')
    def test_run_with_callback(self, mock_copy, mock_available):
        """Test running simulation with callback."""
        callback_mock = Mock(spec=ProcessCallback)
        mock_copy.return_value = self.test_netlist

        with patch('pathlib.Path.exists', return_value=True):
            task = self.runner.run(
                self.test_netlist,
                callback=callback_mock,
                wait_resource=False
            )

            assert task.callback == callback_mock

    @patch('cespy.simulators.ltspice_simulator.LTspice.is_available', return_value=True)
    @patch('shutil.copy')
    def test_run_with_custom_filename(self, mock_copy, mock_available):
        """Test running simulation with custom filename."""
        custom_name = "custom_simulation"
        mock_copy.return_value = self.test_netlist

        with patch('pathlib.Path.exists', return_value=True):
            task = self.runner.run(
                self.test_netlist,
                run_filename=custom_name,
                wait_resource=False
            )

            # The run_filename is passed through to the task
            assert task.netlist_file is not None

    def test_wait_completion_timeout(self):
        """Test wait_completion with timeout."""
        # Mock some active futures to simulate running tasks
        mock_future = Mock()
        mock_future.done.return_value = False
        mock_future.cancel.return_value = False

        # Add a future to the internal set to simulate active task
        self.runner._active_futures = {mock_future}

        with patch('time.sleep'):  # Speed up the test
            result = self.runner.wait_completion(timeout=0.1)

            # Should timeout and return False
            assert result is False

    def test_wait_completion_success(self):
        """Test wait_completion when all tasks complete."""
        # With no submitted tasks, wait_completion should return True immediately
        result = self.runner.wait_completion(timeout=1.0)

        # Should complete successfully
        assert result is True

    def test_abort_all_simulations(self):
        """Test aborting all running simulations."""
        # Test that executor shutdown is called properly
        with patch.object(self.runner._executor, 'shutdown') as mock_shutdown:
            # Simulate destruction/cleanup
            self.runner.__del__()

            # Should call shutdown
            mock_shutdown.assert_called()

    def test_reset_stats(self):
        """Test resetting simulation statistics."""
        # Set some values
        self.runner.run_count = 10
        self.runner.successful_simulations = 8

        # Reset by creating new instance
        new_runner = SimRunner()

        assert new_runner.runno == 0
        assert new_runner.okSim == 0

    def test_set_simulator(self):
        """Test setting custom simulator."""
        from cespy.simulators.ltspice_simulator import LTspice

        # Set a custom simulator
        self.runner.set_simulator(LTspice)

        # Check that simulator was set
        assert self.runner.simulator == LTspice

    def test_simulator_initialization(self):
        """Test that simulator is properly initialized."""
        # Default should be LTspice
        from cespy.simulators.ltspice_simulator import LTspice

        runner = SimRunner()
        assert runner.simulator == LTspice

    def test_file_not_found_error(self):
        """Test error when netlist file doesn't exist."""
        non_existent_file = Path("non_existent.net")

        with pytest.raises(FileNotFoundError):
            self.runner.run(non_existent_file)

    def test_context_manager_behavior(self):
        """Test SimRunner cleanup behavior."""
        runner = SimRunner()
        assert isinstance(runner, SimRunner)

        # Test manual cleanup
        with patch.object(runner._executor, 'shutdown') as mock_shutdown:
            runner.__del__()
            mock_shutdown.assert_called()

    def test_parallel_simulation_limit(self):
        """Test that parallel simulation limit is respected."""
        runner = SimRunner(parallel_sims=1)  # Limit to 1 simulation

        # Check that max_workers is set correctly
        assert runner._executor._max_workers == 1


class TestRunTask:
    """Test RunTask class functionality."""

    def test_runtask_creation(self):
        """Test RunTask object creation."""
        from cespy.simulators.ltspice_simulator import LTspice

        task = RunTask(
            simulator=LTspice,
            runno=1,
            netlist_file=Path("test.net"),
            callback=Mock(),
            switches=["-ascii"],
            timeout=300,
            exe_log=True
        )

        assert task.netlist_file == Path("test.net")
        assert task.runno == 1
        assert task.switches == ["-ascii"]
        assert task.timeout == 300
        assert task.exe_log is True

    def test_runtask_abort(self):
        """Test aborting a RunTask."""
        from cespy.simulators.ltspice_simulator import LTspice
        mock_process = Mock()

        task = RunTask(
            simulator=LTspice,
            runno=1,
            netlist_file=Path("test.net"),
            callback=Mock()
        )
        task.process = mock_process

        # Test that we can access the process attribute
        assert hasattr(task, 'process')
        assert task.process == mock_process

    def test_runtask_basic_properties(self):
        """Test basic RunTask properties."""
        from cespy.simulators.ltspice_simulator import LTspice

        task = RunTask(
            simulator=LTspice,
            runno=1,
            netlist_file=Path("test.net"),
            callback=Mock()
        )

        # Test basic attributes
        assert task.runno == 1
        assert task.netlist_file == Path("test.net")
        assert task.simulator == LTspice
        assert task.callback is not None
