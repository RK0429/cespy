"""Unit tests for SimRunner class functionality."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
from cespy.sim.sim_runner import SimRunner, RunTask
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
        self.runner._runno += 1
        
        assert self.runner.runno == initial_runno + 1

    def test_okSim_property(self):
        """Test okSim property tracks successful simulations."""
        initial_ok = self.runner.okSim
        
        # Simulate successful simulation
        self.runner._okSim += 1
        
        assert self.runner.okSim == initial_ok + 1

    @patch('cespy.sim.sim_runner.SimRunner._get_available_simulator')
    def test_run_single_simulation(self, mock_get_sim):
        """Test running a single simulation."""
        # Mock simulator
        mock_simulator = Mock()
        mock_simulator.run.return_value = 0
        mock_get_sim.return_value = mock_simulator
        
        # Create a test netlist file
        with patch('pathlib.Path.exists', return_value=True):
            task = self.runner.run(self.test_netlist, wait_resource=False)
            
            assert isinstance(task, RunTask)
            mock_get_sim.assert_called_once()

    def test_run_with_switches(self):
        """Test running simulation with command line switches."""
        with patch('cespy.sim.sim_runner.SimRunner._get_available_simulator') as mock_get_sim:
            mock_simulator = Mock()
            mock_simulator.run.return_value = 0
            mock_get_sim.return_value = mock_simulator
            
            with patch('pathlib.Path.exists', return_value=True):
                switches = ["-ascii", "-alt"]
                task = self.runner.run(
                    self.test_netlist,
                    switches=switches,
                    wait_resource=False
                )
                
                assert task.switches == switches

    def test_run_with_callback(self):
        """Test running simulation with callback."""
        callback_mock = Mock(spec=ProcessCallback)
        
        with patch('cespy.sim.sim_runner.SimRunner._get_available_simulator') as mock_get_sim:
            mock_simulator = Mock()
            mock_simulator.run.return_value = 0
            mock_get_sim.return_value = mock_simulator
            
            with patch('pathlib.Path.exists', return_value=True):
                task = self.runner.run(
                    self.test_netlist,
                    callback=callback_mock,
                    wait_resource=False
                )
                
                assert task.callback == callback_mock

    def test_run_with_custom_filename(self):
        """Test running simulation with custom filename."""
        custom_name = "custom_simulation"
        
        with patch('cespy.sim.sim_runner.SimRunner._get_available_simulator') as mock_get_sim:
            mock_simulator = Mock()
            mock_simulator.run.return_value = 0
            mock_get_sim.return_value = mock_simulator
            
            with patch('pathlib.Path.exists', return_value=True):
                task = self.runner.run(
                    self.test_netlist,
                    run_filename=custom_name,
                    wait_resource=False
                )
                
                assert custom_name in str(task.run_filename)

    def test_wait_completion_timeout(self):
        """Test wait_completion with timeout."""
        # Mock some running tasks
        self.runner._pool = Mock()
        self.runner._pool.__len__ = Mock(return_value=1)  # One task running
        
        with patch('time.sleep'):  # Speed up the test
            result = self.runner.wait_completion(timeout=0.1)
            
            # Should timeout and return False
            assert result is False

    def test_wait_completion_success(self):
        """Test wait_completion when all tasks complete."""
        # Mock empty pool (no running tasks)
        self.runner._pool = Mock()
        self.runner._pool.__len__ = Mock(return_value=0)
        
        result = self.runner.wait_completion(timeout=1.0)
        
        # Should complete successfully
        assert result is True

    def test_abort_all_simulations(self):
        """Test aborting all running simulations."""
        # Mock running tasks
        mock_task1 = Mock()
        mock_task2 = Mock()
        self.runner._pool = [mock_task1, mock_task2]
        
        self.runner.abort_all()
        
        # Should abort all tasks
        mock_task1.abort.assert_called_once()
        mock_task2.abort.assert_called_once()
        assert len(self.runner._pool) == 0

    def test_reset_stats(self):
        """Test resetting simulation statistics."""
        # Set some values
        self.runner._runno = 10
        self.runner._okSim = 8
        
        self.runner.reset_stats()
        
        assert self.runner.runno == 0
        assert self.runner.okSim == 0

    @patch('cespy.simulators.ltspice_simulator.LTspice.is_available')
    def test_get_available_simulator_ltspice(self, mock_available):
        """Test getting LTspice simulator when available."""
        mock_available.return_value = True
        
        simulator = self.runner._get_available_simulator("ltspice")
        
        # Should return LTspice class
        from cespy.simulators.ltspice_simulator import LTspice
        assert simulator == LTspice

    @patch('cespy.simulators.ngspice_simulator.NGspice.is_available')
    def test_get_available_simulator_ngspice(self, mock_available):
        """Test getting NGspice simulator when available."""
        mock_available.return_value = True
        
        simulator = self.runner._get_available_simulator("ngspice")
        
        # Should return NGspice class
        from cespy.simulators.ngspice_simulator import NGspice
        assert simulator == NGspice

    def test_get_available_simulator_invalid(self):
        """Test error when requesting invalid simulator."""
        with pytest.raises(ValueError, match="Unknown simulator"):
            self.runner._get_available_simulator("invalid_simulator")

    def test_get_available_simulator_not_available(self):
        """Test error when simulator not available."""
        with patch('cespy.simulators.ltspice_simulator.LTspice.is_available', return_value=False):
            with pytest.raises(RuntimeError, match="ltspice simulator is not available"):
                self.runner._get_available_simulator("ltspice")

    def test_file_not_found_error(self):
        """Test error when netlist file doesn't exist."""
        non_existent_file = Path("non_existent.net")
        
        with pytest.raises(FileNotFoundError):
            self.runner.run(non_existent_file)

    def test_context_manager_behavior(self):
        """Test SimRunner as context manager."""
        with patch('cespy.sim.sim_runner.SimRunner.abort_all') as mock_abort:
            with SimRunner() as runner:
                assert isinstance(runner, SimRunner)
            
            # Should call abort_all on exit
            mock_abort.assert_called_once()

    def test_parallel_simulation_limit(self):
        """Test that parallel simulation limit is respected."""
        runner = SimRunner(parallel_sims=1)  # Limit to 1 simulation
        
        # Mock simulator availability
        with patch('cespy.sim.sim_runner.SimRunner._get_available_simulator') as mock_get_sim:
            mock_simulator = Mock()
            mock_simulator.run.return_value = 0
            mock_get_sim.return_value = mock_simulator
            
            with patch('pathlib.Path.exists', return_value=True):
                # Start first simulation
                task1 = runner.run(self.test_netlist, wait_resource=False)
                
                # Pool should have space for only one more
                assert len(runner._pool) <= runner.parallel_sims


class TestRunTask:
    """Test RunTask class functionality."""

    def test_runtask_creation(self):
        """Test RunTask object creation."""
        task = RunTask(
            circuit_file=Path("test.net"),
            run_filename="test_1",
            simulator_class=Mock(),
            switches=["-ascii"],
            timeout=300,
            callback=Mock(),
            exe_log=True
        )
        
        assert task.circuit_file == Path("test.net")
        assert task.run_filename == "test_1"
        assert task.switches == ["-ascii"]
        assert task.timeout == 300
        assert task.exe_log is True

    def test_runtask_abort(self):
        """Test aborting a RunTask."""
        mock_process = Mock()
        
        task = RunTask(
            circuit_file=Path("test.net"),
            run_filename="test_1",
            simulator_class=Mock()
        )
        task.process = mock_process
        
        task.abort()
        
        mock_process.terminate.assert_called_once()

    def test_runtask_is_running(self):
        """Test checking if RunTask is running."""
        task = RunTask(
            circuit_file=Path("test.net"),
            run_filename="test_1",
            simulator_class=Mock()
        )
        
        # Without process, should not be running
        assert not task.is_running()
        
        # With mock process
        mock_process = Mock()
        mock_process.poll.return_value = None  # Still running
        task.process = mock_process
        
        assert task.is_running()
        
        # Process finished
        mock_process.poll.return_value = 0  # Finished
        assert not task.is_running()