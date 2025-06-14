"""Tests to ensure all functionality from kuPyLTSpice and kupicelib is preserved."""

import pytest
from pathlib import Path
import shutil
from cespy.editor import SpiceEditor, AscEditor, QschEditor
from cespy.simulators import LTspice, NGspice, Qspice, Xyce
from cespy.sim import SimRunner, SimBatch
from cespy.raw import RawRead, RawWrite, Trace
from cespy.log import LTSpiceLogReader, SemiDevOpReader
from cespy.utils import sweep_log, sweep_lin, Histogram
from cespy.client_server import SimServer, SimClient
import numpy as np


class TestEditorFunctionality:
    """Test all editor functionality is preserved."""

    def test_spice_editor_component_operations(self, temp_dir: Path):
        """Test SpiceEditor component manipulation."""
        netlist_path = temp_dir / "test_spice.net"
        netlist_content = """* Test Circuit
V1 in 0 1
R1 in out 1k
C1 out 0 1u
.param gain=10
.tran 1m
.end
"""
        netlist_path.write_text(netlist_content)
        
        # Test SpiceEditor operations
        editor = SpiceEditor(netlist_path)
        
        # Component value operations
        assert editor.get_component_value("R1") == "1k"
        editor.set_component_value("R1", "2.2k")
        assert editor.get_component_value("R1") == "2.2k"
        
        # Parameter operations
        assert editor.get_parameter("gain") == "10"
        editor.set_parameter("gain", "20")
        assert editor.get_parameter("gain") == "20"
        
        # Add new parameter
        editor.set_parameter("offset", "1.5")
        assert editor.get_parameter("offset") == "1.5"
        
        # Component info
        components = editor.get_components()
        assert "V1" in components
        assert "R1" in components
        assert "C1" in components
        
        # Add instruction
        editor.add_instruction(".meas tran vout_avg AVG V(out)")
        
        # Remove instruction
        editor.remove_instruction(".tran 1m")
        
        # Save and verify
        editor.save_netlist()
        
        # Re-read and verify changes
        editor2 = SpiceEditor(netlist_path)
        assert editor2.get_component_value("R1") == "2.2k"
        assert editor2.get_parameter("gain") == "20"
        assert ".meas" in str(editor2)
        assert ".tran" not in str(editor2)
    
    @pytest.mark.requires_ltspice
    def test_asc_editor_operations(self, temp_dir: Path):
        """Test AscEditor schematic manipulation."""
        # Find a test .asc file
        test_asc = Path(__file__).parent.parent.parent.parent / "kupicelib/examples/testfiles/TRAN.asc"
        if not test_asc.exists():
            pytest.skip("Test .asc file not found")
        
        asc_file = temp_dir / "test.asc"
        shutil.copy(test_asc, asc_file)
        
        # Test AscEditor operations
        editor = AscEditor(asc_file)
        
        # Get components
        components = editor.get_components()
        assert len(components) > 0
        
        # Get and set component values
        for comp_ref in components:
            comp = editor.get_component(comp_ref)
            if comp and hasattr(comp, 'value'):
                old_value = comp.value
                # Set a new value
                editor.set_component_value(comp_ref, "100")
                assert editor.get_component_value(comp_ref) == "100"
                # Restore
                editor.set_component_value(comp_ref, old_value)
        
        # Get instructions
        instructions = editor.get_instructions()
        assert len(instructions) > 0
        
        # Save changes
        editor.save()
        
        # Verify file was saved
        assert asc_file.exists()
    
    @pytest.mark.requires_qspice
    def test_qsch_editor_operations(self, temp_dir: Path):
        """Test QschEditor schematic manipulation."""
        # Find a test .qsch file
        test_qsch = Path(__file__).parent.parent.parent.parent / "kupicelib/examples/testfiles/DC sweep.qsch"
        if not test_qsch.exists():
            pytest.skip("Test .qsch file not found")
        
        qsch_file = temp_dir / "test.qsch"
        shutil.copy(test_qsch, qsch_file)
        
        # Test QschEditor operations
        editor = QschEditor(qsch_file)
        
        # Get components
        components = editor.get_components()
        assert len(components) > 0
        
        # Test component operations similar to AscEditor
        # QschEditor should have similar functionality
        
        # Save changes
        editor.save()
        assert qsch_file.exists()


class TestSimulationFunctionality:
    """Test all simulation functionality is preserved."""

    def test_sim_runner_basic(self, temp_dir: Path):
        """Test basic SimRunner functionality."""
        netlist_path = temp_dir / "test_runner.net"
        netlist_content = """* SimRunner Test
V1 in 0 1
R1 in out 1k
C1 out 0 1u
.op
.end
"""
        netlist_path.write_text(netlist_content)
        
        # Test SimRunner operations
        runner = SimRunner()
        
        # Check parallel runs setting
        runner.set_max_parallel_runs(4)
        assert runner.max_parallel_runs == 4
        
        # Check timeout setting
        runner.set_simulation_timeout(60)
        assert runner.timeout == 60
    
    @pytest.mark.requires_ltspice
    def test_sim_batch_functionality(self, temp_dir: Path):
        """Test SimBatch functionality from kuPyLTSpice."""
        base_netlist = temp_dir / "batch_base.net"
        base_content = """* Batch Test
.param Rval=1k
V1 in 0 1
R1 in out {Rval}
C1 out 0 1u
.op
.end
"""
        base_netlist.write_text(base_content)
        
        # Create SimBatch instance
        batch = SimBatch(base_netlist)
        
        # Add parameter variations
        batch.add_parameter_variation("Rval", ["1k", "2k", "5k", "10k"])
        
        # Run batch simulation
        results = batch.run(simulator=LTspice())
        
        # Should have 4 results
        assert len(results) == 4
        
        # Each result should be a tuple of (raw_file, log_file)
        for raw_file, log_file in results:
            assert Path(raw_file).exists()
            assert Path(log_file).exists()
    
    def test_simulator_detection(self):
        """Test that all simulators can be detected."""
        # Test LTspice detection
        ltspice = LTspice()
        # Should have detected executable or set to empty list
        assert hasattr(ltspice, 'spice_exe')
        
        # Test other simulators
        ngspice = NGspice()
        assert hasattr(ngspice, 'spice_exe')
        
        qspice = Qspice() 
        assert hasattr(qspice, 'spice_exe')
        
        xyce = Xyce()
        assert hasattr(xyce, 'spice_exe')


class TestRawFileFunctionality:
    """Test all raw file functionality is preserved."""

    def test_raw_read_write_roundtrip(self, temp_dir: Path):
        """Test reading and writing raw files."""
        # Create test data
        time = np.linspace(0, 1e-3, 100)
        voltage = np.sin(2 * np.pi * 1000 * time)
        current = voltage / 1000
        
        # Create traces
        traces = [
            Trace("time", "time", data=time),
            Trace("V(out)", "voltage", data=voltage),
            Trace("I(R1)", "current", data=current)
        ]
        
        # Write raw file
        raw_file = temp_dir / "test_roundtrip.raw"
        writer = RawWrite(raw_file, "Transient Test", 1e-6)
        for trace in traces:
            writer.add_trace(trace)
        writer.write()
        
        # Read it back
        reader = RawRead(raw_file)
        
        # Verify all traces
        assert len(reader.get_trace_names()) == 3
        
        # Verify data integrity
        time_read = reader.get_trace("time").data
        np.testing.assert_array_almost_equal(time, time_read, decimal=6)
        
        voltage_read = reader.get_trace("V(out)").data
        np.testing.assert_array_almost_equal(voltage, voltage_read, decimal=6)
        
        current_read = reader.get_trace("I(R1)").data
        np.testing.assert_array_almost_equal(current, current_read, decimal=6)
    
    def test_raw_file_properties(self, temp_dir: Path):
        """Test raw file property access."""
        # Create a raw file with specific properties
        raw_file = temp_dir / "test_props.raw"
        writer = RawWrite(raw_file, "Test Analysis", 1.0)
        writer.set_no_points(50)
        writer.set_no_variables(2)
        writer.add_trace(Trace("x", "independent", data=np.linspace(0, 1, 50)))
        writer.add_trace(Trace("y", "dependent", data=np.linspace(0, 1, 50)**2))
        writer.write()
        
        # Read and check properties
        reader = RawRead(raw_file)
        assert reader.get_raw_property("No. Points") == 50
        assert reader.get_raw_property("No. Variables") == 2
        assert reader.get_raw_property("Plotname") == "Test Analysis"


class TestLogFileFunctionality:
    """Test all log file functionality is preserved."""

    def test_ltspice_log_reader(self, temp_dir: Path):
        """Test LTSpice log file reading."""
        log_content = """Circuit: * Test Circuit

Direct Newton iteration for .op point succeeded.

Semiconductor Device Operating Points:

        --- BSIM3 MOSFETS ---
Name:       m1           m2
Model:      nmos        pmos
Id:        1.00e-03   -1.00e-03
Vgs:       2.00e+00   -2.00e+00
Vds:       3.00e+00   -3.00e+00
Vbs:       0.00e+00    0.00e+00
Vth:       7.00e-01   -7.00e-01
Vdsat:     1.30e+00   -1.30e+00

        --- Bipolar Transistors ---
Name:       q1
Model:      npn
Ic:         5.00e-04
Vbe:        7.00e-01
Vce:        2.00e+00

Date: Mon Jan 01 12:00:00 2024
Total elapsed time: 0.234 seconds.

tnom = 27
temp = 27
method = modified trap
totiter = 2345
traniter = 2340
tranpoints = 782
accept = 782
rejected = 0
matrix size = 15
fillins = 3
solver = Normal
"""
        log_file = temp_dir / "test.log"
        log_file.write_text(log_content)
        
        # Test log reader
        reader = LTSpiceLogReader(log_file)
        
        # Check parameters
        assert reader.get_parameter("tnom") == 27
        assert reader.get_parameter("temp") == 27
        assert reader.get_parameter("totiter") == 2345
        assert reader.get_parameter("matrix size") == 15
        
        # Test semiconductor device reader
        semi_reader = SemiDevOpReader(log_file)
        
        # Check MOSFETs
        mosfets = semi_reader.get_mosfets()
        assert len(mosfets) == 2
        assert mosfets[0]["name"] == "m1"
        assert mosfets[0]["Id"] == pytest.approx(1e-3)
        assert mosfets[1]["name"] == "m2"
        assert mosfets[1]["model"] == "pmos"
        
        # Check BJTs
        bjts = semi_reader.get_bjts()
        assert len(bjts) == 1
        assert bjts[0]["name"] == "q1"
        assert bjts[0]["Ic"] == pytest.approx(5e-4)


class TestUtilityFunctionality:
    """Test all utility functionality is preserved."""

    def test_sweep_functions(self):
        """Test parameter sweep utility functions."""
        # Test linear sweep
        lin_values = list(sweep_lin(1, 10, 10))
        assert len(lin_values) == 10
        assert lin_values[0] == 1
        assert lin_values[-1] == 10
        
        # Test logarithmic sweep
        log_values = list(sweep_log(1, 1000, 4))
        assert len(log_values) == 4
        assert log_values[0] == pytest.approx(1)
        assert log_values[1] == pytest.approx(10)
        assert log_values[2] == pytest.approx(100)
        assert log_values[3] == pytest.approx(1000)
    
    def test_histogram_functionality(self):
        """Test Histogram utility class."""
        # Create test data
        data = np.random.normal(0, 1, 1000)
        
        # Create histogram
        hist = Histogram(data, bins=20)
        
        # Check basic properties
        assert hist.n_bins == 20
        assert len(hist.bins) == 20
        assert len(hist.counts) == 20
        
        # Check statistics
        assert abs(hist.mean - 0) < 0.1  # Should be close to 0
        assert abs(hist.std - 1) < 0.1   # Should be close to 1
        
        # Test percentile
        p50 = hist.percentile(50)
        assert abs(p50 - hist.median) < 0.01


class TestClientServerFunctionality:
    """Test client-server functionality is preserved."""

    @pytest.mark.slow
    def test_sim_server_client_basic(self, temp_dir: Path):
        """Test basic server-client communication."""
        # This test would require starting a server in background
        # For now, just test that classes can be instantiated
        
        # Test server creation
        server = SimServer(port=0)  # Use port 0 for automatic assignment
        assert hasattr(server, 'port')
        
        # Test client creation
        client = SimClient()
        assert hasattr(client, 'connect')
        assert hasattr(client, 'submit_simulation')
        assert hasattr(client, 'get_results')


class TestBackwardCompatibility:
    """Test backward compatibility with old API."""

    def test_kupicelib_imports(self):
        """Test that common kupicelib imports still work."""
        # These imports should work if backward compatibility is maintained
        try:
            from cespy.editor import SpiceEditor
            from cespy.simulators import LTspice
            from cespy.sim import SimRunner
            from cespy.raw import RawRead, RawWrite
            # All imports successful
            assert True
        except ImportError as e:
            pytest.fail(f"Import failed: {e}")
    
    def test_kuPyLTSpice_style_usage(self, temp_dir: Path):
        """Test that kuPyLTSpice-style usage patterns still work."""
        # Create a simple netlist
        netlist = temp_dir / "compat_test.net"
        netlist.write_text("""* Compatibility Test
V1 in 0 1
R1 in out 1k
.tran 1m
.end
""")
        
        # kuPyLTSpice style workflow
        try:
            # Should be able to create editor
            editor = SpiceEditor(netlist)
            
            # Should be able to modify values
            editor.set_component_value("R1", "2k")
            
            # Should be able to save
            editor.save_netlist()
            
            # All operations successful
            assert True
        except Exception as e:
            pytest.fail(f"Compatibility test failed: {e}")