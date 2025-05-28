"""Unit tests for SpiceEditor class."""

from pathlib import Path
import pytest
from cespy.editor.spice_editor import SpiceEditor, SpiceCircuit


class TestSpiceCircuit:
    """Test SpiceCircuit functionality."""

    def test_create_from_string(self):
        """Test creating a SpiceCircuit from a netlist string."""
        netlist_lines = [
            "* Test Circuit",
            "V1 in 0 1",
            "R1 in out 1k",
            "C1 out 0 1u",
            ".tran 1m",
            ".end"
        ]
        circuit = SpiceCircuit()
        circuit.netlist = netlist_lines

        assert circuit.get_component_value("R1") == "1k"
        assert circuit.get_component_value("C1") == "1u"
        assert circuit.get_component_value("V1") == "1"

    def test_set_component_value(self):
        """Test setting component values."""
        circuit = SpiceCircuit()
        circuit.netlist = ["R1 in out 1k", "C1 out 0 1u"]

        circuit.set_component_value("R1", "2.2k")
        assert circuit.get_component_value("R1") == "2.2k"

        circuit.set_component_value("C1", "100n")
        assert circuit.get_component_value("C1") == "100n"

    def test_parameter_manipulation(self):
        """Test parameter setting and retrieval."""
        circuit = SpiceCircuit()
        circuit.netlist = [".param freq=1k", ".param gain=10"]

        circuit.set_parameter("freq", "2k")
        assert circuit.get_parameter("freq") == "2k"

        circuit.set_parameter("gain", "20")
        assert circuit.get_parameter("gain") == "20"

    def test_add_instruction(self):
        """Test adding SPICE instructions."""
        circuit = SpiceCircuit()
        circuit.netlist = ["R1 in out 1k"]

        circuit.add_instruction(".tran 1m")
        netlist_str = str(circuit)
        assert ".tran 1m" in netlist_str

        circuit.add_instruction(".ac dec 10 1 10k")
        netlist_str = str(circuit)
        assert ".ac dec 10 1 10k" in netlist_str


class TestSpiceEditor:
    """Test SpiceEditor functionality."""

    def test_create_editor(self, temp_dir: Path):
        """Test creating a SpiceEditor instance."""
        netlist_path = temp_dir / "test.net"
        netlist_path.write_text("""* Test Circuit
V1 in 0 1
R1 in out 1k
.end
""")

        editor = SpiceEditor(netlist_path)
        assert editor.circuit_file == netlist_path
        assert len(editor.netlist) > 0

    def test_save_netlist(self, temp_dir: Path):
        """Test saving a modified netlist."""
        netlist_path = temp_dir / "test.net"
        netlist_path.write_text("R1 in out 1k\n.end\n")

        editor = SpiceEditor(netlist_path)
        editor.set_component_value("R1", "2.2k")
        editor.save_netlist()

        # Reload and verify
        new_editor = SpiceEditor(netlist_path)
        assert new_editor.get_component_value("R1") == "2.2k"

    def test_create_blank_netlist(self, temp_dir: Path):
        """Test creating a blank netlist file."""
        netlist_path = temp_dir / "blank.net"

        editor = SpiceEditor(netlist_path, create_blank=True)
        assert netlist_path.exists()
        assert editor.circuit_file == netlist_path

    def test_encoding_detection(self, temp_dir: Path):
        """Test automatic encoding detection."""
        netlist_path = temp_dir / "test_utf8.net"
        # Write with UTF-8 encoding including special characters
        netlist_path.write_text("* Test Circuit with µ\nR1 in out 1kΩ\n.end\n",
                                encoding="utf-8")

        editor = SpiceEditor(netlist_path, encoding="autodetect")
        netlist_str = str(editor)
        assert "µ" in netlist_str
        assert "Ω" in netlist_str

    def test_component_not_found(self, temp_dir: Path):
        """Test handling of non-existent components."""
        netlist_path = temp_dir / "test.net"
        netlist_path.write_text("R1 in out 1k\n.end\n")

        editor = SpiceEditor(netlist_path)

        with pytest.raises(Exception):  # Should raise ComponentNotFoundError
            editor.get_component_value("R2")

    def test_case_insensitive_components(self, temp_dir: Path):
        """Test case-insensitive component handling."""
        netlist_path = temp_dir / "test.net"
        netlist_path.write_text("R1 in out 1k\nr2 out gnd 2k\n.end\n")

        editor = SpiceEditor(netlist_path)

        # Both should work regardless of case
        assert editor.get_component_value("R1") == "1k"
        assert editor.get_component_value("r1") == "1k"
        assert editor.get_component_value("R2") == "2k"
        assert editor.get_component_value("r2") == "2k"

    def test_subcircuit_handling(self, temp_dir: Path):
        """Test subcircuit manipulation."""
        netlist_path = temp_dir / "test.net"
        netlist_path.write_text(""".subckt amp in out vcc vss
R1 in mid 10k
R2 mid out 10k
.ends
X1 input output vdd gnd amp
.end
""")

        editor = SpiceEditor(netlist_path)

        # Test that we can find components in main circuit
        components = editor.get_components()
        component_refs = [comp.ref for comp in components]
        assert "X1" in component_refs

    def test_parameter_stepping(self, temp_dir: Path):
        """Test parameter stepping functionality."""
        netlist_path = temp_dir / "test.net"
        netlist_path.write_text(""".param res=1k
R1 in out {res}
.step param res 1k 10k 1k
.end
""")

        editor = SpiceEditor(netlist_path)

        # Verify parameter and step are present
        assert editor.get_parameter("res") == "1k"
        netlist_str = str(editor)
        assert ".step param res" in netlist_str