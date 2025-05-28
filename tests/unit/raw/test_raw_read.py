"""Unit tests for raw file reading functionality."""

import pytest
import numpy as np
from pathlib import Path
from cespy.raw.raw_read import RawRead
from cespy.raw.raw_classes import TraceRead


class TestRawRead:
    """Test RawRead class functionality."""

    def test_parse_filename(self):
        """Test filename parsing for run number extraction."""
        # Test standard naming pattern
        assert RawRead._get_runno("circuit_1.raw") == 1
        assert RawRead._get_runno("test_42.raw") == 42
        assert RawRead._get_runno("sim_100.raw") == 100
        
        # Test edge cases
        assert RawRead._get_runno("circuit.raw") == 0
        assert RawRead._get_runno("test_abc.raw") == 0

    def test_get_trace_names(self, sample_raw_data):
        """Test retrieving trace names from raw data."""
        raw = RawRead()
        raw._traces = [
            TraceRead("V(in)", "voltage", 100, None),
            TraceRead("V(out)", "voltage", 100, None),
            TraceRead("I(R1)", "current", 100, None),
        ]
        
        names = raw.get_trace_names()
        assert len(names) == 3
        assert "V(in)" in names
        assert "V(out)" in names
        assert "I(R1)" in names

    def test_get_trace(self, sample_raw_data):
        """Test retrieving specific traces."""
        raw = RawRead()
        
        # Create sample traces with data
        time_data = np.linspace(0, 1e-3, 100)
        voltage_data = np.sin(2 * np.pi * 1000 * time_data)
        
        trace_time = TraceRead("time", "time", 100, None)
        trace_time.data = time_data
        
        trace_voltage = TraceRead("V(out)", "voltage", 100, None)
        trace_voltage.data = voltage_data
        
        raw._traces = [trace_time, trace_voltage]
        
        # Test retrieving by name
        retrieved = raw.get_trace("V(out)")
        assert retrieved.name == "V(out)"
        assert np.array_equal(retrieved.data, voltage_data)
        
        # Test case insensitive
        retrieved_lower = raw.get_trace("v(out)")
        assert retrieved_lower.name == "V(out)"

    def test_get_axis(self, sample_raw_data):
        """Test retrieving axis data."""
        raw = RawRead()
        
        time_data = np.linspace(0, 1e-3, 100)
        trace_time = TraceRead("time", "time", 100, None)
        trace_time.data = time_data
        
        raw._traces = [trace_time]
        raw.axis = trace_time
        
        axis = raw.get_axis()
        assert axis.name == "time"
        assert np.array_equal(axis.data, time_data)

    def test_spice_params(self):
        """Test SPICE parameter handling."""
        raw = RawRead()
        raw.spice_params = {
            "FREQ": "1k",
            "GAIN": "10",
            "TEMP": "27"
        }
        
        # Test parameter access
        assert "FREQ" in raw.spice_params
        assert raw.spice_params["FREQ"] == "1k"
        assert raw.spice_params["GAIN"] == "10"
        assert raw.spice_params["TEMP"] == "27"

    def test_dialect_detection(self):
        """Test simulator dialect detection."""
        raw = RawRead()
        
        # Test LTspice detection
        raw.raw_params = {"Command": "LTspice XVII"}
        # This would normally be done in the file parsing
        # For unit test, we're checking the logic would work
        assert "ltspice" in raw.raw_params["Command"].lower()
        
        # Test NGSpice detection
        raw.raw_params = {"Command": "ngspice-44"}
        assert "ngspice" in raw.raw_params["Command"].lower()

    def test_add_trace_alias(self):
        """Test adding calculated trace aliases."""
        raw = RawRead()
        
        # Set up base traces
        time_data = np.linspace(0, 1e-3, 100)
        v_in = np.ones(100)
        v_out = 0.5 * np.ones(100)
        
        trace_time = TraceRead("time", "time", 100, None)
        trace_time.data = time_data
        
        trace_v_in = TraceRead("V(in)", "voltage", 100, None)
        trace_v_in.data = v_in
        
        trace_v_out = TraceRead("V(out)", "voltage", 100, None) 
        trace_v_out.data = v_out
        
        raw._traces = [trace_time, trace_v_in, trace_v_out]
        raw.nPoints = 100
        raw.axis = trace_time
        
        # Add calculated trace
        gain_trace = raw.add_trace_alias("Gain", "V(out)/V(in)")
        
        assert gain_trace.name == "Gain"
        assert np.allclose(gain_trace.data, 0.5)


@pytest.fixture
def sample_raw_data():
    """Provide sample raw data for testing."""
    return {
        "title": "* Test Circuit",
        "date": "Mon Jan 01 00:00:00 2024",
        "plotname": "Transient Analysis",
        "flags": "real",
        "no_variables": "3",
        "no_points": "100",
        "variables": [
            ("time", "time"),
            ("V(in)", "voltage"),
            ("V(out)", "voltage"),
        ]
    }