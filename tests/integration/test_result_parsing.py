"""Integration tests for parsing simulation results (.raw and .log files)."""

import pytest
from pathlib import Path
import numpy as np
from cespy.raw.raw_read import RawRead
from cespy.raw.raw_write import RawWrite, Trace
from cespy.log.ltsteps import LTSpiceLogReader
from cespy.log.semi_dev_op_reader import opLogReader
from cespy.log.qspice_log_reader import QspiceLogReader


class TestRawFileParsing:
    """Test parsing of raw waveform files from different simulators."""

    def test_parse_ltspice_transient_raw(self, temp_dir: Path):
        """Test parsing LTSpice transient analysis raw file."""
        # Create a simple raw file for testing
        traces = [
            Trace("time", "time", data=np.linspace(0, 1e-3, 100)),
            Trace(
                "V(out)",
                "voltage",
                data=np.sin(2 * np.pi * 1000 * np.linspace(0, 1e-3, 100)),
            ),
            Trace(
                "I(R1)",
                "current",
                data=np.sin(2 * np.pi * 1000 * np.linspace(0, 1e-3, 100)) / 1000,
            ),
        ]

        raw_file = temp_dir / "test_tran.raw"
        writer = RawWrite(raw_file, "transient", 1e-6)
        for trace in traces:
            writer.add_trace(trace)
        writer.write()

        # Parse the file
        reader = RawRead(raw_file)

        # Verify header info
        assert reader.get_raw_property("No. Variables") == 3
        assert reader.get_raw_property("Plotname") == "transient"

        # Verify traces
        trace_names = reader.get_trace_names()
        assert "time" in trace_names
        assert "V(out)" in trace_names
        assert "I(R1)" in trace_names

        # Verify data
        time_data = reader.get_trace("time").data
        assert len(time_data) == 100
        assert time_data[0] == 0
        assert time_data[-1] == pytest.approx(1e-3)

        # Verify voltage trace
        voltage_data = reader.get_trace("V(out)").data
        assert len(voltage_data) == 100
        # Check it's a sine wave (starts at 0, goes positive)
        assert voltage_data[0] == pytest.approx(0, abs=1e-6)
        assert voltage_data[25] == pytest.approx(0, abs=0.1)  # Zero crossing

    def test_parse_ac_analysis_raw(self, temp_dir: Path):
        """Test parsing AC analysis raw file with complex data."""
        # Create AC analysis raw file
        frequencies = np.logspace(0, 5, 50)  # 1Hz to 100kHz
        # Complex impedance data
        z_real = 1000 / (1 + (frequencies / 1000) ** 2)
        z_imag = -frequencies / (1 + (frequencies / 1000) ** 2)
        z_complex = z_real + 1j * z_imag

        traces = [
            Trace("frequency", "frequency", data=frequencies),
            Trace("V(out)", "voltage", data=z_complex),
        ]

        raw_file = temp_dir / "test_ac.raw"
        writer = RawWrite(raw_file, "AC Analysis", 1.0)
        for trace in traces:
            writer.add_trace(trace)
        writer.write()

        # Parse the file
        reader = RawRead(raw_file)

        # Verify it's AC analysis (complex data)
        assert reader.get_raw_property("Flags") == "complex"

        # Get frequency axis
        freq_axis = reader.get_axis()
        assert freq_axis.name == "frequency"
        assert len(freq_axis.data) == 50

        # Get complex voltage data
        voltage_trace = reader.get_trace("V(out)")
        assert voltage_trace.data.dtype == complex

        # Verify magnitude decreases with frequency (RC filter behavior)
        magnitudes = np.abs(voltage_trace.data)
        assert magnitudes[0] > magnitudes[-1]

    def test_parse_stepped_data(self, temp_dir: Path):
        """Test parsing raw file with parameter stepping."""
        # Create raw file with stepped data (3 steps)
        num_points = 50
        num_steps = 3

        # Create data for 3 parameter steps
        all_time_data = []
        all_voltage_data = []

        for step in range(num_steps):
            time = np.linspace(0, 1e-3, num_points)
            voltage = (step + 1) * np.sin(2 * np.pi * 1000 * time)
            all_time_data.extend(time)
            all_voltage_data.extend(voltage)

        traces = [
            Trace("time", "time", data=np.array(all_time_data)),
            Trace("V(out)", "voltage", data=np.array(all_voltage_data)),
        ]

        raw_file = temp_dir / "test_stepped.raw"
        writer = RawWrite(raw_file, "Transient Analysis", 1e-6)
        writer.set_no_points(num_points)
        writer.set_no_steps(num_steps)
        for trace in traces:
            writer.add_trace(trace)
        writer.write()

        # Parse the file
        reader = RawRead(raw_file)

        # Verify step information
        assert reader.get_raw_property("No. Points") == num_points
        assert reader.nsteps == num_steps

        # Get data for each step
        for step in range(num_steps):
            step_data = reader.get_trace("V(out)", step=step)
            assert len(step_data.data) == num_points
            # Verify amplitude increases with step
            max_voltage = np.max(np.abs(step_data.data))
            assert max_voltage == pytest.approx(step + 1, rel=0.1)

    def test_parse_operating_point(self, temp_dir: Path):
        """Test parsing operating point analysis raw file."""
        # Create operating point raw file
        traces = [
            Trace("V(in)", "voltage", data=np.array([5.0])),
            Trace("V(out)", "voltage", data=np.array([2.5])),
            Trace("I(Vsource)", "current", data=np.array([0.0025])),
        ]

        raw_file = temp_dir / "test_op.raw"
        writer = RawWrite(raw_file, "Operating Point", 1.0)
        for trace in traces:
            writer.add_trace(trace)
        writer.write()

        # Parse the file
        reader = RawRead(raw_file)

        # Operating point should have single values
        v_in = reader.get_trace("V(in)").data
        assert len(v_in) == 1
        assert v_in[0] == 5.0

        v_out = reader.get_trace("V(out)").data
        assert len(v_out) == 1
        assert v_out[0] == 2.5


class TestLogFileParsing:
    """Test parsing of log files from different simulators."""

    def test_parse_ltspice_log_basic(self, temp_dir: Path):
        """Test parsing basic LTSpice log file."""
        log_content = """Circuit: * Test Circuit

Direct Newton iteration for .op point succeeded.

Date: Mon Jan 01 12:00:00 2024
Total elapsed time: 0.123 seconds.

tnom = 27
temp = 27
method = trap
totiter = 543
traniter = 540
tranpoints = 271
accept = 271
rejected = 0
matrix size = 5
fillins = 0
solver = Normal
"""
        log_file = temp_dir / "test.log"
        log_file.write_text(log_content)

        # Parse log file
        reader = LTSpiceLogReader(log_file)

        # Check basic info
        assert reader.get_parameter("tnom") == 27
        assert reader.get_parameter("temp") == 27
        assert reader.get_parameter("method") == "trap"
        assert reader.get_parameter("totiter") == 543

    def test_parse_ltspice_log_with_steps(self, temp_dir: Path):
        """Test parsing LTSpice log file with parameter steps."""
        log_content = """Circuit: * Parameter Sweep Test

.step Rval=1k
Direct Newton iteration for .op point succeeded.

.step Rval=2k
Direct Newton iteration for .op point succeeded.

.step Rval=3k
Direct Newton iteration for .op point succeeded.

Date: Mon Jan 01 12:00:00 2024
Total elapsed time: 0.456 seconds.
"""
        log_file = temp_dir / "test_steps.log"
        log_file.write_text(log_content)

        # Parse log file
        reader = LTSpiceLogReader(log_file)

        # Get steps
        steps = reader.get_steps()
        assert len(steps) == 3

        # Verify step values
        assert steps[0]["Rval"] == "1k"
        assert steps[1]["Rval"] == "2k"
        assert steps[2]["Rval"] == "3k"

    def test_parse_device_operating_points(self, temp_dir: Path):
        """Test parsing semiconductor device operating points."""
        log_content = """Circuit: * Test Circuit

Semiconductor Device Operating Points:

Name:       m1
Model:    nmos_model
Id:       1.23e-03
Vgs:      2.50e+00
Vds:      5.00e+00
Vbs:      0.00e+00
Vth:      7.50e-01
Vdsat:    1.75e+00
Gm:       2.46e-03
Gds:      1.23e-05
Gmb:      5.00e-04

Name:       q1
Model:    npn_model
Ic:       5.00e-04
Vbe:      7.00e-01
Vce:      3.00e+00
Vbc:     -2.30e+00
Beta:     100
Gm:       1.92e-02

Date: Mon Jan 01 12:00:00 2024
"""
        log_file = temp_dir / "test_devices.log"
        log_file.write_text(log_content)

        # Parse semiconductor operating points
        reader = opLogReader(log_file)

        # Get MOSFET data
        mosfets = reader.get_mosfets()
        assert len(mosfets) == 1
        assert mosfets[0]["name"] == "m1"
        assert mosfets[0]["Id"] == pytest.approx(1.23e-3)
        assert mosfets[0]["Vgs"] == pytest.approx(2.5)
        assert mosfets[0]["Vth"] == pytest.approx(0.75)

        # Get BJT data
        bjts = reader.get_bjts()
        assert len(bjts) == 1
        assert bjts[0]["name"] == "q1"
        assert bjts[0]["Ic"] == pytest.approx(5e-4)
        assert bjts[0]["Beta"] == pytest.approx(100)

    @pytest.mark.requires_qspice
    def test_parse_qspice_log(self, temp_dir: Path):
        """Test parsing Qspice log file."""
        log_content = """Qspice64 1.2.3
Circuit: Test Circuit

Number of threads: 4
Simulation started at: 12:00:00

.tran 0 1m 0 1u
Total time step: 1000
Time to simulate: 0.234s

Measurement Results:
.meas tran vout_rms RMS V(out)
vout_rms = 0.707

.meas tran period TRIG V(out) VAL=0 RISE=1 TARG V(out) VAL=0 RISE=2
period = 1.000e-03

Total simulation time: 0.567s
"""
        log_file = temp_dir / "test_qspice.log"
        log_file.write_text(log_content)

        # Parse Qspice log
        reader = QspiceLogReader(log_file)

        # Get measurements
        measurements = reader.get_measurements()
        assert "vout_rms" in measurements
        assert measurements["vout_rms"] == pytest.approx(0.707)
        assert "period" in measurements
        assert measurements["period"] == pytest.approx(1e-3)


class TestRawFileCompatibility:
    """Test raw file compatibility across simulators."""

    def test_ltspice_ngspice_raw_compatibility(self, temp_dir: Path):
        """Test reading LTSpice raw files vs NGSpice raw files."""
        # Both simulators use similar raw format, but with slight differences

        # Create traces
        time = np.linspace(0, 1e-3, 100)
        voltage = np.sin(2 * np.pi * 1000 * time)

        traces = [
            Trace("time", "time", data=time),
            Trace("v(out)", "voltage", data=voltage),  # NGSpice uses lowercase
        ]

        # Write as "NGSpice" style
        ngspice_raw = temp_dir / "ngspice.raw"
        writer = RawWrite(ngspice_raw, "Transient Analysis", 1e-6)
        for trace in traces:
            writer.add_trace(trace)
        writer.write()

        # Read with automatic dialect detection
        reader = RawRead(ngspice_raw)

        # Should still be able to read the data
        assert reader.get_trace("time") is not None
        assert reader.get_trace("v(out)") is not None

        # Case-insensitive trace lookup should work
        assert reader.get_trace("V(out)") is not None

    def test_ascii_vs_binary_raw(self, temp_dir: Path):
        """Test reading ASCII vs binary raw files."""
        # Create test data
        time = np.linspace(0, 1e-3, 100)
        voltage = np.sin(2 * np.pi * 1000 * time)

        traces = [
            Trace("time", "time", data=time),
            Trace("V(out)", "voltage", data=voltage),
        ]

        # Write binary raw file
        binary_raw = temp_dir / "binary.raw"
        writer_bin = RawWrite(binary_raw, "Transient", 1e-6, binary=True)
        for trace in traces:
            writer_bin.add_trace(trace)
        writer_bin.write()

        # Write ASCII raw file
        ascii_raw = temp_dir / "ascii.raw"
        writer_asc = RawWrite(ascii_raw, "Transient", 1e-6, binary=False)
        for trace in traces:
            writer_asc.add_trace(trace)
        writer_asc.write()

        # Read both files
        reader_bin = RawRead(binary_raw)
        reader_asc = RawRead(ascii_raw)

        # Verify both have same data
        time_bin = reader_bin.get_trace("time").data
        time_asc = reader_asc.get_trace("time").data
        np.testing.assert_array_almost_equal(time_bin, time_asc)

        voltage_bin = reader_bin.get_trace("V(out)").data
        voltage_asc = reader_asc.get_trace("V(out)").data
        np.testing.assert_array_almost_equal(voltage_bin, voltage_asc)
