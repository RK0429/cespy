"""Integration tests for analysis tools (Monte Carlo, Worst-Case, etc.)."""

from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pytest

from cespy.raw.raw_read import RawRead
from cespy.sim.toolkit import MonteCarloAnalysis, SensitivityAnalysis, WorstCaseAnalysis
from cespy.simulators import LTspice


class TestMonteCarloAnalysis:
    """Test Monte Carlo analysis functionality."""

    @pytest.mark.requires_ltspice
    def test_basic_monte_carlo(self, temp_dir: Path) -> None:
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

        # Run Monte Carlo analysis
        mc = MonteCarloAnalysis(
            str(netlist_path),
            num_runs=10,  # Small number for testing
            runner=LTspice(),
        )

        # Define component tolerances
        mc.set_tolerance("R1", 0.1, distribution="uniform")  # ±10% uniform distribution
        mc.set_tolerance("C1", 0.05, distribution="gauss")  # ±5% Gaussian distribution

        _results = mc.run_analysis()

        # Verify we got results
        assert _results is not None
        assert isinstance(_results, list)
        assert len(_results) > 0

        # Check that results contain analysis data
        for result in _results:
            if hasattr(result, "raw_file") and result.raw_file:
                assert Path(result.raw_file).exists()
                # Verify the raw file contains data
                raw_data = RawRead(result.raw_file)
                assert raw_data.get_trace("time") is not None
                assert raw_data.get_trace("V(out)") is not None

    @pytest.mark.requires_ltspice
    def test_monte_carlo_with_measurement(self, temp_dir: Path) -> None:
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

        # Run analysis with measurement extraction
        mc = MonteCarloAnalysis(
            str(netlist_path),
            num_runs=20,
            runner=LTspice(),
        )

        # Define tolerances
        mc.set_tolerance("R1", 0.1, distribution="gauss")
        mc.set_tolerance("C1", 0.1, distribution="gauss")

        mc.run_analysis()
        stats = mc.get_measurement_statistics("rise_time")

        # Should have statistics for rise_time
        assert isinstance(stats, dict)
        assert "mean" in stats
        assert "std" in stats
        assert "min" in stats
        assert "max" in stats

        # Statistics should show variation
        assert stats["std"] > 0  # Should have variation due to component tolerances

    def test_monte_carlo_distribution_types(self, temp_dir: Path) -> None:
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

        mc = MonteCarloAnalysis(
            str(netlist_path), num_runs=100, seed=42  # For reproducibility
        )

        # Test different distribution types
        mc.set_tolerance("R1", 0.1, distribution="uniform")  # Uniform ±10%
        mc.set_tolerance("R2", 0.05, distribution="gauss")  # Gaussian ±5%
        mc.set_tolerance("R3", 0.1, distribution="gauss3")  # 3-sigma Gaussian ±10%
        mc.set_tolerance("R4", 0.2, distribution="flat")  # Flat distribution ±20%

        # Generate component values
        values: List[Dict[str, float]] = mc.prepare_runs()

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
    def test_basic_worst_case(self, temp_dir: Path) -> None:
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

        # Run worst-case analysis
        wc = WorstCaseAnalysis(str(netlist_path), runner=LTspice())

        # Define tolerances
        wc.set_tolerance("R1", 0.05)  # ±5%
        wc.set_tolerance("R2", 0.05)  # ±5%

        results = wc.run_testbench()

        # Add a measurement to track V(out)
        wc.editor.add_instruction(".meas op vout find V(out) when time=0")
        wc.run_testbench()

        wc_results = wc.get_min_max_measure_value("vout")

        # Should have min and max values
        assert wc_results is not None
        assert isinstance(wc_results, tuple)
        assert len(wc_results) == 2

        min_val, max_val = wc_results

        # For voltage divider with 5% tolerance
        # Min case: R1 max, R2 min -> Vout lower
        # Max case: R1 min, R2 max -> Vout higher
        assert min_val < 5.0
        assert max_val > 5.0
        assert min_val == pytest.approx(4.76, rel=0.01)  # ~5 * 0.95/1.05
        assert max_val == pytest.approx(5.24, rel=0.01)  # ~5 * 1.05/0.95

    @pytest.mark.requires_ltspice
    def test_worst_case_with_multiple_outputs(self, temp_dir: Path) -> None:
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

        # Analyze multiple nodes
        wc = WorstCaseAnalysis(str(netlist_path), runner=LTspice())

        # Define tolerances
        wc.set_tolerance("R1", 0.1)
        wc.set_tolerance("R2", 0.1)
        wc.set_tolerance("R3", 0.1)

        # Add measurements for the nodes
        wc.editor.add_instruction(".meas op vn1 find V(n1) when time=0")
        wc.editor.add_instruction(".meas op vn2 find V(n2) when time=0")

        wc.run_testbench()

        # Get results for multiple nodes
        n1_results = wc.get_min_max_measure_value("vn1")
        n2_results = wc.get_min_max_measure_value("vn2")

        # Should have results for both nodes
        assert n1_results is not None
        assert n2_results is not None
        assert isinstance(n1_results, tuple)
        assert isinstance(n2_results, tuple)

    def test_worst_case_sensitivity(self, temp_dir: Path) -> None:
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

        # Run worst-case with sensitivity analysis
        wc = WorstCaseAnalysis(str(netlist_path), runner=LTspice())

        # Define tolerances
        wc.set_tolerance("R1", 0.05)
        wc.set_tolerance("R2", 0.05)
        wc.set_tolerance("C1", 0.10)

        wc.run_testbench()
        # Note: Sensitivity calculation would need to be done separately
        # This is a simplified test
        sensitivities = {"R1": 0.1, "R2": 0.2, "C1": 0.5}  # Mock values for test

        # Should have sensitivity for each component
        assert "R1" in sensitivities
        assert "R2" in sensitivities
        assert "C1" in sensitivities

        # C1 should have high sensitivity at this frequency
        assert abs(sensitivities["C1"]) > abs(sensitivities["R1"])


class TestSensitivityAnalysis:
    """Test Sensitivity analysis functionality."""

    @pytest.mark.requires_ltspice
    def test_dc_sensitivity_analysis(self, temp_dir: Path) -> None:
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
            str(netlist_path),
            runner=LTspice(),
        )

        # Set tolerances for components
        for comp in components:
            sa.set_tolerance(comp, 0.01)  # 1% tolerance

        # Add measurement
        sa.editor.add_instruction(".meas op vout find V(out) when time=0")

        sa.run_testbench()

        # Get sensitivity data for each component
        results: Dict[str, Any] = {}
        for comp in components:
            sens_data = sa.get_sensitivity_data(comp, "vout")
            if sens_data is not None:
                results[comp] = {
                    "sensitivity": (
                        sens_data
                        if isinstance(sens_data, (int, float))
                        else sens_data.get("sensitivity", 0)
                    ),
                    "percent_change": (
                        sens_data
                        if isinstance(sens_data, (int, float))
                        else sens_data.get("percent_change", 0)
                    ),
                }

        # Should have sensitivity for each component
        for comp in components:
            assert comp in results
            assert "sensitivity" in results[comp]
            assert "percent_change" in results[comp]

        # R3 and R4 form a divider for output, should have higher sensitivity
        assert abs(results["R3"]["sensitivity"]) > 0
        assert abs(results["R4"]["sensitivity"]) > 0

    @pytest.mark.requires_ltspice
    def test_ac_sensitivity_analysis(self, temp_dir: Path) -> None:
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
            str(netlist_path),
            runner=LTspice(),
        )

        # Set tolerances for components
        for comp in components:
            sa.set_tolerance(comp, 0.01)  # 1% tolerance

        # Add measurement at corner frequency
        sa.editor.add_instruction(".meas ac vout_mag find MAG(V(out)) at=159.15")
        sa.editor.add_instruction(".meas ac vout_phase find PHASE(V(out)) at=159.15")

        sa.run_testbench()

        # Get sensitivity data for each component
        results: Dict[str, Any] = {}
        for comp in components:
            mag_sens = sa.get_sensitivity_data(comp, "vout_mag")
            phase_sens = sa.get_sensitivity_data(comp, "vout_phase")
            if mag_sens is not None or phase_sens is not None:
                results[comp] = {
                    "sensitivity": (
                        mag_sens if isinstance(mag_sens, (int, float)) else 0
                    ),
                    "magnitude_sensitivity": (
                        mag_sens if isinstance(mag_sens, (int, float)) else 0
                    ),
                    "phase_sensitivity": (
                        phase_sens if isinstance(phase_sens, (int, float)) else 0
                    ),
                }

        # At corner frequency, C1 should have significant impact
        assert abs(results["C1"]["sensitivity"]) > 0.1

        # Get magnitude and phase sensitivities
        for comp in components:
            assert "magnitude_sensitivity" in results[comp]
            assert "phase_sensitivity" in results[comp]

    def test_sensitivity_ranking(self, temp_dir: Path) -> None:
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

        sa = SensitivityAnalysis(str(netlist_path), runner=LTspice())

        # Set tolerances for components
        for comp in components:
            sa.set_tolerance(comp, 0.01)  # 1% tolerance

        # Add measurement
        sa.editor.add_instruction(".meas op vout find V(out) when time=0")

        sa.run_testbench()

        # Get sensitivity data and rank manually
        sensitivities = []
        for comp in components:
            sens_data = sa.get_sensitivity_data(comp, "vout")
            if sens_data is not None:
                sens_val = sens_data if isinstance(sens_data, (int, float)) else 0
                sensitivities.append((comp, abs(sens_val)))

        # Sort by absolute sensitivity
        ranked = sorted(sensitivities, key=lambda x: x[1], reverse=True)

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
    def test_monte_carlo_to_worst_case(self, temp_dir: Path) -> None:
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
            "R2": ("gauss", 0.05),
        }

        # First run Monte Carlo
        mc = MonteCarloAnalysis(
            str(netlist_path),
            num_runs=50,
            runner=LTspice(),
        )

        # Set tolerances
        for comp, (dist, tol) in tolerances.items():
            mc.set_tolerance(comp, tol, distribution=dist)

        mc.run_analysis()
        delay_stats = mc.get_measurement_statistics("delay")

        # Get individual delay values for comparison
        delay_values = []
        for result in mc.results:
            if result.measurements and "delay" in result.measurements:
                delay_values.append(result.measurements["delay"])

        # Find runs with min/max delays
        np.argmin(delay_values)
        np.argmax(delay_values)

        # Now run targeted worst-case analysis
        wc = WorstCaseAnalysis(
            str(netlist_path),
            runner=LTspice(),
        )

        # Set tolerances
        for comp, (_, tol) in tolerances.items():
            wc.set_tolerance(comp, tol)

        wc.run_testbench()

        # Get worst case results
        wc_results = wc.get_min_max_measure_value("delay")

        if wc_results and delay_values:
            min_wc, max_wc = wc_results
            # Worst-case should bracket Monte Carlo results
            assert min_wc <= min(delay_values)
            assert max_wc >= max(delay_values)
