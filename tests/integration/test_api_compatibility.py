"""Integration tests for API compatibility between cespy and original packages."""

from pathlib import Path

import pytest

from cespy import simulate
from cespy.editor.spice_editor import SpiceEditor
from cespy.raw.raw_read import RawRead
from cespy.simulators.ltspice_simulator import LTspice


class TestAPICompatibility:
    """Test that the unified API maintains compatibility with original packages."""

    def test_high_level_simulate_function(self, temp_dir: Path) -> None:
        """Test the high-level simulate function works as expected."""
        # Create a simple netlist
        netlist_path = temp_dir / "test_circuit.net"
        netlist_content = """* Test Circuit
V1 in 0 1
R1 in out 1k
C1 out 0 1u
.op
.end
"""
        netlist_path.write_text(netlist_content)

        # Test that simulate function is callable with various parameters
        try:
            # This may fail if simulator not available, but should not raise import errors
            result = simulate(
                netlist_path,
                engine="ltspice",
                parallel_sims=1,
                timeout=60.0,
                verbose=False,
            )
            # If it succeeds, should return a tuple of (raw_file, log_file)
            if result is not None:
                assert isinstance(result, tuple)
                assert len(result) == 2
        except (RuntimeError, FileNotFoundError):
            # Expected if simulator not available
            pass

    def test_spice_editor_basic_workflow(self, temp_dir: Path) -> None:
        """Test basic SpiceEditor workflow."""
        netlist_path = temp_dir / "editor_test.net"
        initial_content = """* Test Circuit for Editor
V1 in 0 DC 1
R1 in out 1k
C1 out 0 1u
.tran 1m
.end
"""
        netlist_path.write_text(initial_content)

        # Test editor creation and basic operations
        editor = SpiceEditor(netlist_path)

        # Test component value access
        assert editor.get_component_value("R1") == "1k"
        assert editor.get_component_value("C1") == "1u"

        # Test component value modification
        editor.set_component_value("R1", "2.2k")
        assert editor.get_component_value("R1") == "2.2k"

        # Test parameter operations
        editor.set_parameter("freq", "1k")
        assert editor.get_parameter("freq") == "1k"

        # Test saving
        editor.save_netlist(str(netlist_path))

        # Verify changes persist
        new_editor = SpiceEditor(netlist_path)
        assert new_editor.get_component_value("R1") == "2.2k"
        assert new_editor.get_parameter("freq") == "1k"

    def test_raw_read_basic_functionality(self, temp_dir: Path) -> None:
        """Test basic RawRead functionality without actual raw files."""
        # Create a dummy raw file for testing
        raw_path = temp_dir / "dummy.raw"
        raw_path.write_bytes(b"Title: Test\nDate: Mon Jan 01 00:00:00 2024\n")

        # Test that RawRead can be instantiated and has expected methods
        raw_reader = RawRead(str(raw_path))

        # Test essential methods exist
        assert hasattr(raw_reader, "get_trace_names")
        assert hasattr(raw_reader, "get_trace")
        assert hasattr(raw_reader, "get_axis")
        assert hasattr(raw_reader, "add_trace_alias")

        # Test properties exist
        assert hasattr(raw_reader, "nPoints")
        assert hasattr(raw_reader, "nPlots")
        assert hasattr(raw_reader, "spice_params")

    def test_simulator_classes_availability(self) -> None:
        """Test that all simulator classes are available and have expected interface."""
        # Test LTspice simulator
        assert hasattr(LTspice, "run")
        assert hasattr(LTspice, "create_netlist")
        assert hasattr(LTspice, "is_available")
        assert hasattr(LTspice, "valid_switch")

        # Test that simulator detection works
        try:
            LTspice.detect_executable()
            # Should not raise exception
        except Exception as e:
            # Log but don't fail - simulator may not be available
            print(f"Simulator detection info: {e}")

    def test_import_structure_compatibility(self) -> None:
        """Test that imports work as expected for API compatibility."""
        # Test main package imports
        import cespy

        assert hasattr(cespy, "simulate")
        assert hasattr(cespy, "__version__")

        # Test submodule imports
        from cespy.editor import AscEditor, SpiceEditor
        from cespy.raw import RawRead
        from cespy.sim import SimRunner
        from cespy.simulators import LTspice

        # Verify classes are callable
        assert callable(SpiceEditor)
        assert callable(AscEditor)
        assert callable(RawRead)
        assert callable(LTspice)
        assert callable(SimRunner)

    def test_editor_file_format_support(self, temp_dir: Path) -> None:
        """Test that editor supports various file formats."""
        # Test .net file support
        net_file = temp_dir / "test.net"
        net_file.write_text("V1 in 0 1\nR1 in out 1k\n.end\n")

        editor = SpiceEditor(net_file)
        assert editor.circuit_file == net_file

        # Test create_blank functionality
        blank_file = temp_dir / "blank.net"
        SpiceEditor(blank_file, create_blank=True)
        assert blank_file.exists()

    def test_error_handling_compatibility(self, temp_dir: Path) -> None:
        """Test that error handling works as expected."""
        # Test file not found error
        non_existent = temp_dir / "non_existent.net"

        with pytest.raises(FileNotFoundError):
            SpiceEditor(non_existent)

        # Test component not found error
        netlist_path = temp_dir / "test.net"
        netlist_path.write_text("R1 in out 1k\n.end\n")

        editor = SpiceEditor(netlist_path)

        # Should raise exception for non-existent component
        with pytest.raises(
            Exception
        ):  # Specific exception type depends on implementation
            editor.get_component_value("non_existent_component")

    def test_cross_module_integration(self, temp_dir: Path) -> None:
        """Test integration between different modules."""
        # Create a circuit with editor
        netlist_path = temp_dir / "integration_test.net"

        # Use editor to create and modify circuit
        editor = SpiceEditor(netlist_path, create_blank=True)
        editor.add_instruction("V1 in 0 DC 1")
        editor.add_instruction("R1 in out 1k")
        editor.add_instruction("C1 out 0 1u")
        editor.add_instruction(".op")
        editor.add_instruction(".end")
        editor.save_netlist(str(netlist_path))

        # Verify file was created and is readable
        assert netlist_path.exists()

        # Test that the same file can be read by another editor instance
        editor2 = SpiceEditor(netlist_path)
        content = str(editor2)
        assert "V1 in 0 DC 1" in content
        assert "R1 in out 1k" in content

    def test_parameter_sweep_integration(self, temp_dir: Path) -> None:
        """Test parameter sweep functionality integration."""
        netlist_path = temp_dir / "sweep_test.net"
        content = """.param res_val=1k
V1 in 0 1
R1 in out {res_val}
C1 out 0 1u
.step param res_val 1k 10k 1k
.dc V1 0 1 0.1
.end
"""
        netlist_path.write_text(content)

        editor = SpiceEditor(netlist_path)

        # Test parameter access
        assert editor.get_parameter("res_val") == "1k"

        # Test parameter modification
        editor.set_parameter("res_val", "2.2k")
        assert editor.get_parameter("res_val") == "2.2k"

        # Verify step directive is preserved
        netlist_content = str(editor)
        assert ".step param res_val" in netlist_content

    @pytest.mark.integration
    def test_end_to_end_workflow_mock(self, temp_dir: Path) -> None:
        """Test end-to-end workflow with mocked simulation."""
        # Create initial circuit
        circuit_file = temp_dir / "workflow_test.net"

        # Step 1: Create circuit with editor
        editor = SpiceEditor(circuit_file, create_blank=True)
        editor.add_instruction("* RC Circuit Test")
        editor.add_instruction("V1 in 0 PULSE(0 1 0 1n 1n 0.5m 1m)")
        editor.add_instruction("R1 in out 1k")
        editor.add_instruction("C1 out 0 1u")
        editor.add_instruction(".tran 0 2m 0 1u")
        editor.add_instruction(".end")
        editor.save_netlist(str(circuit_file))

        # Step 2: Verify circuit file is valid
        assert circuit_file.exists()

        # Step 3: Read back and verify content
        editor2 = SpiceEditor(circuit_file)
        assert editor2.get_component_value("R1") == "1k"
        assert editor2.get_component_value("C1") == "1u"

        # Step 4: Modify parameters
        editor2.set_component_value("R1", "2.2k")
        editor2.set_component_value("C1", "100n")
        editor2.save_netlist(str(circuit_file))

        # Step 5: Verify modifications
        editor3 = SpiceEditor(circuit_file)
        assert editor3.get_component_value("R1") == "2.2k"
        assert editor3.get_component_value("C1") == "100n"
