"""Integration tests for complete simulation workflows."""

import pytest
from pathlib import Path
from cespy import simulate
from cespy.editor.spice_editor import SpiceEditor
from cespy.raw.raw_read import RawRead


class TestSimulationWorkflow:
    """Test complete simulation workflows from netlist to results."""

    @pytest.mark.requires_ltspice
    def test_basic_ltspice_workflow(self, temp_dir: Path):
        """Test basic LTSpice simulation workflow."""
        # Create a simple RC circuit netlist
        netlist_path = temp_dir / "rc_circuit.net"
        netlist_content = """* RC Circuit Test
V1 in 0 PULSE(0 1 0 1n 1n 0.5m 1m)
R1 in out 1k
C1 out 0 1u
.tran 0 2m 0 1u
.end
"""
        netlist_path.write_text(netlist_content)

        # Run simulation
        raw_file, log_file = simulate(netlist_path, simulator="ltspice")

        # Verify output files exist
        assert raw_file.exists()
        assert log_file.exists()

        # Parse and verify results
        raw_data = RawRead(raw_file)

        # Check that expected traces exist
        trace_names = raw_data.get_trace_names()
        assert "time" in trace_names
        assert "V(in)" in trace_names
        assert "V(out)" in trace_names

        # Verify time axis
        time_axis = raw_data.get_axis()
        assert time_axis.data[-1] >= 2e-3  # Should run for at least 2ms

    @pytest.mark.requires_ltspice
    def test_parameter_sweep_workflow(self, temp_dir: Path):
        """Test parameter sweep simulation workflow."""
        # Create netlist with parameter sweep
        netlist_path = temp_dir / "sweep_circuit.net"
        netlist_content = """* Parameter Sweep Test
.param Rval=1k
V1 in 0 1
R1 in out {Rval}
C1 out 0 1u
.dc V1 0 1 0.1
.step param Rval 1k 10k 1k
.end
"""
        netlist_path.write_text(netlist_content)

        # Run simulation
        raw_file, log_file = simulate(netlist_path, simulator="ltspice")

        # Parse results
        raw_data = RawRead(raw_file)

        # Should have multiple steps
        # Note: Implementation would need to handle stepped data
        assert raw_data.get_trace("V(out)") is not None

    def test_edit_and_simulate_workflow(self, temp_dir: Path):
        """Test editing a circuit and simulating."""
        # Create initial netlist
        netlist_path = temp_dir / "edit_test.net"
        initial_content = """* Edit and Simulate Test
V1 in 0 1
R1 in out 1k
C1 out 0 1u
.tran 1m
.end
"""
        netlist_path.write_text(initial_content)

        # Edit the circuit
        editor = SpiceEditor(netlist_path)

        # Change component values
        editor.set_component_value("R1", "2.2k")
        editor.set_component_value("C1", "100n")

        # Add a parameter
        editor.set_parameter("gain", "10")

        # Save changes
        editor.save_netlist()

        # Verify changes were saved
        new_editor = SpiceEditor(netlist_path)
        assert new_editor.get_component_value("R1") == "2.2k"
        assert new_editor.get_component_value("C1") == "100n"
        assert new_editor.get_parameter("gain") == "10"

    @pytest.mark.requires_ngspice
    def test_ngspice_workflow(self, temp_dir: Path):
        """Test NGSpice simulation workflow."""
        # Create NGSpice compatible netlist
        netlist_path = temp_dir / "ngspice_test.net"
        netlist_content = """NGSpice Test Circuit
V1 in 0 DC 1 AC 1
R1 in out 1k
C1 out 0 1u
.ac dec 10 1 10k
.end
"""
        netlist_path.write_text(netlist_content)

        # Run simulation with NGSpice
        raw_file, log_file = simulate(netlist_path, simulator="ngspice")

        # Verify output
        assert raw_file.exists()

        # Parse results
        raw_data = RawRead(raw_file, dialect="ngspice")

        # Check for frequency domain data
        trace_names = raw_data.get_trace_names()
        assert "frequency" in trace_names
        assert "V(out)" in trace_names

    def test_multi_analysis_workflow(self, temp_dir: Path):
        """Test circuit with multiple analyses."""
        # Create netlist with multiple analyses
        netlist_path = temp_dir / "multi_analysis.net"
        netlist_content = """* Multiple Analysis Test
V1 in 0 1
R1 in out 1k
C1 out 0 1u

* Operating point
.op

* DC sweep
.dc V1 0 5 0.1

* AC analysis
.ac dec 10 1 100k

* Transient
.tran 0 1m 0 1u

.end
"""
        netlist_path.write_text(netlist_content)

        # This would need implementation to handle multiple analyses
        # For now, we just verify the netlist is valid
        editor = SpiceEditor(netlist_path)
        assert ".op" in str(editor)
        assert ".dc" in str(editor)
        assert ".ac" in str(editor)
        assert ".tran" in str(editor)
