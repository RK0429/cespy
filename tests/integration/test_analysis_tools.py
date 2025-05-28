"""Integration tests for analysis tools (Monte Carlo, Worst-Case, etc.)."""

import pytest
from pathlib import Path
import numpy as np
from cespy.sim.toolkit import MonteCarloAnalysis, WorstCaseAnalysis, SensitivityAnalysis
from cespy.editor.spice_editor import SpiceEditor
from cespy.simulators import LTspice
from cespy.sim import SimRunner
from cespy.raw.raw_read import RawRead


class TestMonteCarloAnalysis:
    """Test Monte Carlo analysis functionality."""

    @pytest.mark.requires_ltspice
    def test_basic_monte_carlo(self, temp_dir: Path):
        """Test basic Monte Carlo analysis on RC circuit."""
        # Create base netlist
        netlist_path = temp_dir / "rc_monte_carlo.net"
        netlist_content = """* RC Circuit for Monte Carlo
V1 in 0 1
R1 in out 1k
C1 out 0 1u
.tran 0 5m 0 10u
.end
"""
        netlist_path.write_text(netlist_content)
        
        # Define component tolerances
        tolerances = {
            "R1": ("uniform", 0.1),  # ±10% uniform distribution
            "C1": ("gauss", 0.05)    # ±5% Gaussian distribution
        }
        
        # Run Monte Carlo analysis
        mc = MonteCarloAnalysis(
            netlist_path,
            tolerances,
            num_runs=10,  # Small number for testing
            simulator=LTspice()
        )
        
        results = mc.run()
        
        # Verify we got the expected number of results
        assert len(results) == 10
        
        # Each result should have raw and log files
        for raw_file, log_file in results:
            assert Path(raw_file).exists()
            assert Path(log_file).exists()
            
            # Verify the raw file contains data
            raw_data = RawRead(raw_file)
            assert raw_data.get_trace("time") is not None
            assert raw_data.get_trace("V(out)") is not None
    
    @pytest.mark.requires_ltspice
    def test_monte_carlo_with_measurement(self, temp_dir: Path):
        """Test Monte Carlo with measurement extraction."""
        # Create netlist with measurement
        netlist_path = temp_dir / "rc_monte_carlo_meas.net"
        netlist_content = """* RC Circuit with Measurement
V1 in 0 PULSE(0 1 0 1n 1n 1m 2m)
R1 in out 1k
C1 out 0 1u
.tran 0 5m 0 10u
.meas tran rise_time TRIG V(out) VAL=0.1 RISE=1 TARG V(out) VAL=0.9 RISE=1
.end
"""
        netlist_path.write_text(netlist_content)
        
        # Define tolerances
        tolerances = {
            "R1": ("gauss", 0.1),
            "C1": ("gauss", 0.1)
        }
        
        # Run analysis with measurement extraction
        mc = MonteCarloAnalysis(
            netlist_path,
            tolerances,
            num_runs=20,
            simulator=LTspice(),
            measurements=["rise_time"]
        )
        
        results = mc.run()
        measurements = mc.get_measurements()
        
        # Should have rise_time measurements
        assert "rise_time" in measurements
        assert len(measurements["rise_time"]) == 20
        
        # Rise times should vary due to component tolerances
        rise_times = measurements["rise_time"]
        assert np.std(rise_times) > 0  # Should have variation
        
        # Get statistical summary
        stats = mc.get_statistics()
        assert "rise_time" in stats
        assert "mean" in stats["rise_time"]
        assert "std" in stats["rise_time"]
        assert "min" in stats["rise_time"]
        assert "max" in stats["rise_time"]
    
    def test_monte_carlo_distribution_types(self, temp_dir: Path):
        """Test different distribution types for Monte Carlo."""
        netlist_path = temp_dir / "test_distributions.net"
        netlist_content = """* Test Distributions
V1 1 0 1
R1 1 2 1k
R2 2 3 2k
R3 3 4 3k
R4 4 0 4k
.op
.end
"""
        netlist_path.write_text(netlist_content)
        
        # Test different distribution types
        tolerances = {
            "R1": ("uniform", 0.1),    # Uniform ±10%
            "R2": ("gauss", 0.05),     # Gaussian ±5%
            "R3": ("gauss3", 0.1),     # 3-sigma Gaussian ±10%
            "R4": ("flat", 0.2)        # Flat distribution ±20%
        }
        
        mc = MonteCarloAnalysis(
            netlist_path,
            tolerances,
            num_runs=100,
            seed=42  # For reproducibility
        )
        
        # Generate component values
        values = mc._generate_component_values()
        
        # Verify distributions
        assert len(values) == 100
        
        # Check that values are within expected ranges
        for run_values in values:
            # R1 uniform: should be between 900 and 1100
            assert 900 <= run_values["R1"] <= 1100
            
            # R2 gaussian: most should be within 1900-2100
            assert 1800 <= run_values["R2"] <= 2200
            
            # R4 flat: should be between 3200 and 4800
            assert 3200 <= run_values["R4"] <= 4800


class TestWorstCaseAnalysis:
    """Test Worst-Case analysis functionality."""

    @pytest.mark.requires_ltspice
    def test_basic_worst_case(self, temp_dir: Path):
        """Test basic worst-case analysis."""
        # Create voltage divider circuit
        netlist_path = temp_dir / "voltage_divider_wc.net"
        netlist_content = """* Voltage Divider Worst Case
V1 in 0 10
R1 in out 10k
R2 out 0 10k
.op
.end
"""
        netlist_path.write_text(netlist_content)
        
        # Define tolerances
        tolerances = {
            "R1": 0.05,  # ±5%
            "R2": 0.05   # ±5%
        }
        
        # Run worst-case analysis
        wc = WorstCaseAnalysis(
            netlist_path,
            tolerances,
            output_node="out",
            simulator=LTspice()
        )
        
        results = wc.run()
        
        # Should have min and max cases
        assert "min" in results
        assert "max" in results
        
        # For voltage divider, nominal should be 5V
        # Min case: R1 max, R2 min -> Vout lower
        # Max case: R1 min, R2 max -> Vout higher
        assert results["min"]["V(out)"] < 5.0
        assert results["max"]["V(out)"] > 5.0
        assert results["nominal"]["V(out)"] == pytest.approx(5.0, rel=0.01)
    
    @pytest.mark.requires_ltspice
    def test_worst_case_with_multiple_outputs(self, temp_dir: Path):
        """Test worst-case analysis with multiple output nodes."""
        netlist_path = temp_dir / "multi_output_wc.net"
        netlist_content = """* Multi-Output Circuit
V1 in 0 10
R1 in n1 1k
R2 n1 n2 2k
R3 n2 0 3k
.op
.end
"""
        netlist_path.write_text(netlist_content)
        
        tolerances = {
            "R1": 0.1,
            "R2": 0.1,
            "R3": 0.1
        }
        
        # Analyze multiple nodes
        wc = WorstCaseAnalysis(
            netlist_path,
            tolerances,
            output_node=["n1", "n2"],
            simulator=LTspice()
        )
        
        results = wc.run()
        
        # Should have results for both nodes
        assert "V(n1)" in results["nominal"]
        assert "V(n2)" in results["nominal"]
        assert "V(n1)" in results["min"]
        assert "V(n2)" in results["max"]
    
    def test_worst_case_sensitivity(self, temp_dir: Path):
        """Test sensitivity calculation in worst-case analysis."""
        netlist_path = temp_dir / "sensitivity_test.net"
        netlist_content = """* Sensitivity Test Circuit
V1 in 0 1
R1 in n1 1k
C1 n1 out 1u
R2 out 0 10k
.ac dec 10 1 10k
.end
"""
        netlist_path.write_text(netlist_content)
        
        tolerances = {
            "R1": 0.05,
            "R2": 0.05,
            "C1": 0.10
        }
        
        # Run worst-case with sensitivity analysis
        wc = WorstCaseAnalysis(
            netlist_path,
            tolerances,
            output_node="out",
            frequency=1000,  # Analyze at 1kHz
            calculate_sensitivity=True
        )
        
        results = wc.run()
        sensitivities = wc.get_sensitivities()
        
        # Should have sensitivity for each component
        assert "R1" in sensitivities
        assert "R2" in sensitivities
        assert "C1" in sensitivities
        
        # C1 should have high sensitivity at this frequency
        assert abs(sensitivities["C1"]) > abs(sensitivities["R1"])


class TestSensitivityAnalysis:
    """Test Sensitivity analysis functionality."""

    @pytest.mark.requires_ltspice
    def test_dc_sensitivity_analysis(self, temp_dir: Path):
        """Test DC sensitivity analysis."""
        netlist_path = temp_dir / "dc_sensitivity.net"
        netlist_content = """* DC Sensitivity Test
V1 in 0 10
R1 in n1 1k
R2 n1 0 2k
R3 n1 out 3k
R4 out 0 4k
.op
.end
"""
        netlist_path.write_text(netlist_content)
        
        # Components to analyze
        components = ["R1", "R2", "R3", "R4"]
        
        # Run sensitivity analysis
        sa = SensitivityAnalysis(
            netlist_path,
            components,
            output_node="out",
            analysis_type="dc",
            simulator=LTspice()
        )
        
        results = sa.run()
        
        # Should have sensitivity for each component
        for comp in components:
            assert comp in results
            assert "sensitivity" in results[comp]
            assert "percent_change" in results[comp]
        
        # R3 and R4 form a divider for output, should have higher sensitivity
        assert abs(results["R3"]["sensitivity"]) > 0
        assert abs(results["R4"]["sensitivity"]) > 0
    
    @pytest.mark.requires_ltspice
    def test_ac_sensitivity_analysis(self, temp_dir: Path):
        """Test AC sensitivity analysis at specific frequency."""
        netlist_path = temp_dir / "ac_sensitivity.net"
        netlist_content = """* AC Sensitivity Test
V1 in 0 AC 1
R1 in n1 1k
C1 n1 0 1u
R2 n1 out 10k
C2 out 0 100n
.ac dec 20 1 100k
.end
"""
        netlist_path.write_text(netlist_content)
        
        components = ["R1", "R2", "C1", "C2"]
        
        # Analyze at corner frequency
        sa = SensitivityAnalysis(
            netlist_path,
            components,
            output_node="out",
            analysis_type="ac",
            frequency=159.15,  # ~1/(2*pi*R1*C1)
            simulator=LTspice()
        )
        
        results = sa.run()
        
        # At corner frequency, C1 should have significant impact
        assert abs(results["C1"]["sensitivity"]) > 0.1
        
        # Get magnitude and phase sensitivities
        for comp in components:
            assert "magnitude_sensitivity" in results[comp]
            assert "phase_sensitivity" in results[comp]
    
    def test_sensitivity_ranking(self, temp_dir: Path):
        """Test ranking components by sensitivity."""
        netlist_path = temp_dir / "ranking_test.net"
        netlist_content = """* Sensitivity Ranking Test
V1 in 0 10
R1 in n1 100
R2 n1 n2 1k
R3 n2 out 10k
R4 out 0 100k
.op
.end
"""
        netlist_path.write_text(netlist_content)
        
        components = ["R1", "R2", "R3", "R4"]
        
        sa = SensitivityAnalysis(
            netlist_path,
            components,
            output_node="out",
            analysis_type="dc"
        )
        
        results = sa.run()
        ranked = sa.get_ranked_sensitivities()
        
        # Should return components ranked by absolute sensitivity
        assert len(ranked) == 4
        
        # R3 and R4 should have highest impact on output
        top_components = [item[0] for item in ranked[:2]]
        assert "R3" in top_components or "R4" in top_components
        
        # R1 should have lowest impact (small value, far from output)
        assert ranked[-1][0] == "R1"


class TestAnalysisToolsIntegration:
    """Test integration between different analysis tools."""

    @pytest.mark.requires_ltspice
    def test_monte_carlo_to_worst_case(self, temp_dir: Path):
        """Test using Monte Carlo results to inform worst-case analysis."""
        netlist_path = temp_dir / "integration_test.net"
        netlist_content = """* Integration Test Circuit
V1 in 0 PULSE(0 1 0 1n 1n 1m 2m)
R1 in n1 1k
C1 n1 out 1u
R2 out 0 10k
.tran 0 3m 0 10u
.meas tran delay TRIG V(in) VAL=0.5 RISE=1 TARG V(out) VAL=0.5 RISE=1
.end
"""
        netlist_path.write_text(netlist_content)
        
        tolerances = {
            "R1": ("gauss", 0.05),
            "C1": ("gauss", 0.10),
            "R2": ("gauss", 0.05)
        }
        
        # First run Monte Carlo
        mc = MonteCarloAnalysis(
            netlist_path,
            tolerances,
            num_runs=50,
            measurements=["delay"],
            simulator=LTspice()
        )
        
        mc_results = mc.run()
        mc_stats = mc.get_statistics()
        
        # Identify worst-case directions from Monte Carlo
        delay_mean = mc_stats["delay"]["mean"]
        delay_values = mc.get_measurements()["delay"]
        
        # Find runs with min/max delays
        min_idx = np.argmin(delay_values)
        max_idx = np.argmax(delay_values)
        
        # Now run targeted worst-case analysis
        wc = WorstCaseAnalysis(
            netlist_path,
            {k: v[1] for k, v in tolerances.items()},  # Extract tolerance values
            measurement="delay",
            simulator=LTspice()
        )
        
        wc_results = wc.run()
        
        # Worst-case should bracket Monte Carlo results
        assert wc_results["min"]["delay"] <= min(delay_values)
        assert wc_results["max"]["delay"] >= max(delay_values)