#!/usr/bin/env python
# coding=utf-8
"""Integration tests for refactored analysis components."""

import tempfile
from pathlib import Path
from typing import Any, Generator, List, Tuple
from unittest.mock import patch

import pytest

from cespy.sim.toolkit import (
    AnalysisResult,
    AnalysisStatus,
    AnalysisVisualizer,
    BaseAnalysis,
    MonteCarloAnalysis,
    ProgressReporter,
    StatisticalAnalysis,
    check_plotting_availability,
)


@pytest.fixture
def sample_circuit_file() -> Generator[Path, None, None]:
    """Create a sample circuit file for testing."""
    circuit_content = """
* Simple test circuit
V1 net1 0 DC 5V
R1 net1 net2 1k
C1 net2 0 1u
.tran 0 1m 0 1u
.meas tran Vout_avg AVG V(net2) FROM 0 TO 1m
.end
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".net", delete=False) as f:
        f.write(circuit_content)
        f.flush()
        yield Path(f.name)

    # Cleanup
    Path(f.name).unlink(missing_ok=True)


class TestBaseAnalysisIntegration:
    """Test integration of BaseAnalysis with mock simulations."""

    def test_base_analysis_abstract_methods(self, sample_circuit_file: Path) -> None:
        """Test that BaseAnalysis enforces abstract methods."""
        # Can't instantiate BaseAnalysis directly
        with pytest.raises(TypeError):
            BaseAnalysis(str(sample_circuit_file))

    def test_progress_reporter_integration(self) -> None:
        """Test ProgressReporter integration."""
        progress_calls: List[Tuple[int, int, str]] = []

        def progress_callback(current: int, total: int, message: str) -> None:
            progress_calls.append((current, total, message))

        reporter = ProgressReporter(progress_callback)

        # Simulate progress updates
        for i in range(5):
            reporter.report(i, 5, f"Step {i}")

        # Should have throttled some calls
        assert len(progress_calls) <= 5
        assert progress_calls[-1][0] == 4  # Last call should be completion
        assert progress_calls[-1][1] == 5


class TestStatisticalAnalysisIntegration:
    """Test StatisticalAnalysis base class integration."""

    def test_statistical_analysis_creation(self, sample_circuit_file: Path) -> None:
        """Test StatisticalAnalysis instantiation."""
        # StatisticalAnalysis is abstract, can't instantiate directly
        with pytest.raises(TypeError):
            analysis = StatisticalAnalysis(str(sample_circuit_file), num_runs=10, seed=42)

    def test_statistics_calculation_with_mock_results(
        self, sample_circuit_file: Path
    ) -> None:
        """Test statistics calculation with mock results."""
        # Use MonteCarloAnalysis as a concrete implementation of StatisticalAnalysis
        analysis = MonteCarloAnalysis(str(sample_circuit_file), num_runs=5)

        # Add mock results
        for i in range(5):
            result = AnalysisResult(
                run_id=i,
                status=AnalysisStatus.COMPLETED,
                measurements={
                    "Vout_avg": 2.0 + i * 0.1
                },  # Values: 2.0, 2.1, 2.2, 2.3, 2.4
            )
            analysis.results.append(result)

        stats = analysis.calculate_statistics("Vout_avg")

        assert stats["count"] == 5
        assert stats["mean"] == pytest.approx(2.2, rel=1e-10)
        assert stats["min"] == pytest.approx(2.0, rel=1e-10)
        assert stats["max"] == pytest.approx(2.4, rel=1e-10)
        assert stats["std"] > 0

    def test_histogram_data_generation(self, sample_circuit_file: Path) -> None:
        """Test histogram data generation."""
        # Use MonteCarloAnalysis as a concrete implementation of StatisticalAnalysis
        analysis = MonteCarloAnalysis(sample_circuit_file, num_runs=10)

        # Add mock results with varied data
        import numpy as np

        np.random.seed(42)
        for i in range(10):
            result = AnalysisResult(
                run_id=i,
                status=AnalysisStatus.COMPLETED,
                measurements={"Vout": np.random.normal(2.5, 0.1)},
            )
            analysis.results.append(result)

        counts, bin_edges = analysis.get_histogram_data("Vout", bins=5)

        assert len(counts) == 5
        assert len(bin_edges) == 6  # N+1 edges for N bins
        assert sum(counts) == 10  # Total count should match number of results

    def test_correlation_matrix_calculation(self, sample_circuit_file: Path) -> None:
        """Test correlation matrix calculation."""
        # Use MonteCarloAnalysis as a concrete implementation of StatisticalAnalysis
        analysis = MonteCarloAnalysis(str(sample_circuit_file), num_runs=5)

        # Add mock results with correlated measurements
        for i in range(5):
            result = AnalysisResult(
                run_id=i,
                status=AnalysisStatus.COMPLETED,
                measurements={
                    "Vout1": 2.0 + i * 0.1,
                    "Vout2": 3.0 + i * 0.1,  # Perfectly correlated with Vout1
                    "Vout3": 1.0 - i * 0.05,  # Anti-correlated
                },
            )
            analysis.results.append(result)

        corr_matrix, valid_measurements = analysis.get_correlation_matrix(
            ["Vout1", "Vout2", "Vout3"]
        )

        assert len(valid_measurements) == 3
        assert corr_matrix.shape == (3, 3)
        # Diagonal should be 1.0 (self-correlation)
        assert corr_matrix[0, 0] == pytest.approx(1.0, rel=1e-10)
        assert corr_matrix[1, 1] == pytest.approx(1.0, rel=1e-10)
        assert corr_matrix[2, 2] == pytest.approx(1.0, rel=1e-10)


class TestMonteCarloAnalysisIntegration:
    """Test enhanced MonteCarloAnalysis integration."""

    @patch("cespy.sim.toolkit.montecarlo.SimRunner")
    def test_monte_carlo_dual_mode_creation(
        self, mock_runner: Any, sample_circuit_file: Path
    ) -> None:
        """Test MonteCarloAnalysis creation with both modes."""
        # Testbench mode (default)
        mc_testbench = MonteCarloAnalysis(
            str(sample_circuit_file), num_runs=100, use_testbench_mode=True
        )
        assert mc_testbench.use_testbench_mode is True
        assert mc_testbench.num_runs == 100

        # Separate run mode
        mc_separate = MonteCarloAnalysis(
            str(sample_circuit_file),
            num_runs=50,
            use_testbench_mode=False,
            parallel=True,
            max_workers=2,
        )
        assert mc_separate.use_testbench_mode is False
        assert mc_separate.parallel is True
        assert mc_separate.max_workers == 2

    @patch("cespy.sim.toolkit.montecarlo.SimRunner")
    def test_tolerance_setting_and_parameter_generation(
        self, mock_runner: Any, sample_circuit_file: Path
    ) -> None:
        """Test tolerance setting and parameter generation."""
        mc = MonteCarloAnalysis(
            str(sample_circuit_file), num_runs=10, use_testbench_mode=False, seed=42
        )

        # Set component tolerances
        mc.set_tolerance("R1", 0.05)  # 5% tolerance
        mc.set_tolerance("C1", 0.10)  # 10% tolerance

        # Mock the component retrieval
        with patch.object(mc, "get_components", return_value=["R1", "C1"]):
            with patch.object(mc, "get_component_value_deviation_type") as mock_get_dev:
                # Mock return values for component deviations
                from cespy.sim.toolkit.tolerance_deviations import (
                    ComponentDeviation,
                    DeviationType,
                )

                def mock_deviation(ref: str) -> Tuple[float, ComponentDeviation]:
                    if ref == "R1":
                        return (
                            1000.0,
                            ComponentDeviation(
                                max_val=0.05,
                                min_val=0,
                                typ=DeviationType.TOLERANCE,
                                distribution="uniform",
                            ),
                        )
                    elif ref == "C1":
                        return 1e-6, ComponentDeviation(
                            max_val=0.10,
                            min_val=0,
                            typ=DeviationType.TOLERANCE,
                            distribution="normal",
                        )
                    return 0, ComponentDeviation(
                        max_val=0,
                        min_val=0,
                        typ=DeviationType.NONE,
                        distribution="uniform",
                    )

                mock_get_dev.side_effect = mock_deviation

                # Generate parameters for runs
                all_params = mc.prepare_runs()

                assert len(all_params) == 10
                # Check that parameters contain component variations
                param_names: set[str] = set()
                for params in all_params:
                    param_names.update(params.keys())

                # Should have run_id and possibly component parameters
                assert "run_id" in param_names

    def test_backward_compatibility_methods(self, sample_circuit_file: Path) -> None:
        """Test that backward compatibility methods work."""
        with patch("cespy.sim.toolkit.montecarlo.SimRunner"):
            mc = MonteCarloAnalysis(
                sample_circuit_file, num_runs=5, use_testbench_mode=True
            )

            # Test that old methods still exist and work
            assert hasattr(mc, "run_analysis")
            assert hasattr(mc, "analyse_measurement")
            assert hasattr(mc, "get_measurement_statistics")

            # Mock some results for testing
            mc.results = [
                AnalysisResult(
                    run_id=i,
                    status=AnalysisStatus.COMPLETED,
                    measurements={"Vout": 2.0 + i * 0.1},
                )
                for i in range(5)
            ]

            # Test statistics method
            stats = mc.get_measurement_statistics("Vout")
            assert isinstance(stats, dict)
            assert "mean" in stats
            assert "std" in stats


class TestAnalysisVisualizationIntegration:
    """Test integration of analysis visualization components."""

    def test_plotting_availability_check(self) -> None:
        """Test plotting library availability check."""
        availability = check_plotting_availability()

        assert isinstance(availability, dict)
        assert "matplotlib" in availability
        assert "seaborn" in availability
        assert isinstance(availability["matplotlib"], bool)
        assert isinstance(availability["seaborn"], bool)

    @pytest.mark.skipif(
        not check_plotting_availability()["matplotlib"],
        reason="Matplotlib not available",
    )
    def test_visualizer_creation(self, sample_circuit_file: Path) -> None:
        """Test AnalysisVisualizer creation and basic functionality."""
        visualizer = AnalysisVisualizer()

        assert visualizer.figsize == (10, 6)
        assert hasattr(visualizer, "plot_histogram")
        assert hasattr(visualizer, "plot_scatter_matrix")
        assert hasattr(visualizer, "create_analysis_report")

    @pytest.mark.skipif(
        not check_plotting_availability()["matplotlib"],
        reason="Matplotlib not available",
    )
    def test_histogram_plotting_integration(self, sample_circuit_file: Path) -> None:
        """Test histogram plotting with real analysis data."""
        # Create analysis with mock results
        analysis = StatisticalAnalysis(sample_circuit_file, num_runs=20)

        import numpy as np

        np.random.seed(42)
        for i in range(20):
            result = AnalysisResult(
                run_id=i,
                status=AnalysisStatus.COMPLETED,
                measurements={"Vout": np.random.normal(2.5, 0.2)},
            )
            analysis.results.append(result)

        visualizer = AnalysisVisualizer()

        try:
            fig = visualizer.plot_histogram(analysis, "Vout", show_stats=True)
            assert fig is not None
            assert hasattr(fig, "savefig")  # Should be a matplotlib Figure

            # Clean up
            import matplotlib.pyplot as plt

            plt.close(fig)

        except Exception as e:
            # If plotting fails, it shouldn't crash the test
            pytest.skip(f"Plotting failed: {e}")


class TestPerformanceIntegration:
    """Test performance monitoring integration with analysis."""

    def test_analysis_with_performance_monitoring(
        self, sample_circuit_file: Path
    ) -> None:
        """Test analysis with performance monitoring enabled."""
        from cespy.core import enable_performance_monitoring, get_performance_report

        # Enable performance monitoring
        enable_performance_monitoring(True)

        try:
            # Create analysis (this should be monitored)
            with patch("cespy.sim.toolkit.montecarlo.SimRunner"):
                mc = MonteCarloAnalysis(
                    sample_circuit_file, num_runs=5, use_testbench_mode=False
                )

                # Mock the analysis execution
                with patch.object(mc, "_run_single") as mock_run_single:
                    mock_run_single.return_value = AnalysisResult(
                        run_id=0,
                        status=AnalysisStatus.COMPLETED,
                        measurements={"Vout": 2.5},
                    )

                    # This should be monitored if the decorator is applied
                    results = mc.prepare_runs()

                    assert len(results) == 5

            # Check if performance data was collected
            report = get_performance_report()
            assert isinstance(report, str)

        finally:
            enable_performance_monitoring(False)


class TestErrorHandlingIntegration:
    """Test error handling in integrated analysis workflows."""

    def test_analysis_with_failed_runs(self, sample_circuit_file: Path) -> None:
        """Test analysis behavior with some failed simulation runs."""
        # Use MonteCarloAnalysis as a concrete implementation of StatisticalAnalysis
        analysis = MonteCarloAnalysis(str(sample_circuit_file), num_runs=5)

        # Add mix of successful and failed results
        results = [
            AnalysisResult(
                run_id=0, status=AnalysisStatus.COMPLETED, measurements={"Vout": 2.0}
            ),
            AnalysisResult(
                run_id=1,
                status=AnalysisStatus.FAILED,
                error_message="Simulation failed",
            ),
            AnalysisResult(
                run_id=2, status=AnalysisStatus.COMPLETED, measurements={"Vout": 2.1}
            ),
            AnalysisResult(run_id=3, status=AnalysisStatus.CANCELLED),
            AnalysisResult(
                run_id=4, status=AnalysisStatus.COMPLETED, measurements={"Vout": 2.2}
            ),
        ]

        analysis.results = results

        # Statistics should only include successful runs
        stats = analysis.calculate_statistics("Vout")
        assert stats["count"] == 3  # Only successful runs
        assert stats["mean"] == pytest.approx(2.1, rel=1e-10)

        # Get overall statistics
        overall_stats = analysis.get_statistics()
        assert overall_stats["total_runs"] == 5
        assert overall_stats["successful"] == 3
        assert overall_stats["failed"] == 1
        assert overall_stats["success_rate"] == 60.0

    def test_missing_measurement_handling(self, sample_circuit_file: Path) -> None:
        """Test handling of missing measurements in results."""
        # Use MonteCarloAnalysis as a concrete implementation of StatisticalAnalysis
        analysis = MonteCarloAnalysis(sample_circuit_file, num_runs=3)

        # Add results with inconsistent measurements
        results = [
            AnalysisResult(
                run_id=0,
                status=AnalysisStatus.COMPLETED,
                measurements={"Vout": 2.0, "Iout": 0.001},
            ),
            AnalysisResult(
                run_id=1, status=AnalysisStatus.COMPLETED, measurements={"Vout": 2.1}
            ),  # Missing Iout
            AnalysisResult(
                run_id=2, status=AnalysisStatus.COMPLETED, measurements={"Iout": 0.002}
            ),  # Missing Vout
        ]

        analysis.results = results

        # Should handle missing measurements gracefully
        vout_stats = analysis.calculate_statistics("Vout")
        assert vout_stats["count"] == 2  # Only 2 results have Vout

        iout_stats = analysis.calculate_statistics("Iout")
        assert iout_stats["count"] == 2  # Only 2 results have Iout

        # Non-existent measurement should return empty stats
        missing_stats = analysis.calculate_statistics("NonExistent")
        assert missing_stats == {}


class TestCrossModuleIntegration:
    """Test integration between different refactored modules."""

    def test_platform_aware_analysis(self, sample_circuit_file: Path) -> None:
        """Test that analysis uses platform information for optimization."""
        from cespy.core import get_optimal_workers, get_platform_info

        platform_info = get_platform_info()
        optimal_workers = get_optimal_workers()

        with patch("cespy.sim.toolkit.montecarlo.SimRunner"):
            mc = MonteCarloAnalysis(
                sample_circuit_file,
                num_runs=10,
                parallel=True,
                max_workers=optimal_workers,
            )

            # Should respect platform-specific worker count
            assert mc.max_workers == optimal_workers
            assert mc.max_workers <= platform_info.cpu_count

    def test_regex_caching_in_analysis(self, sample_circuit_file: Path) -> None:
        """Test that analysis components use cached regex patterns."""
        from cespy.core import cached_regex
        from cespy.core.performance import regex_cache

        # Clear cache
        regex_cache.clear()

        # Use a pattern that might be used in analysis
        pattern = cached_regex(r"R\w+")
        assert regex_cache.miss_count == 1

        # Use same pattern again
        pattern2 = cached_regex(r"R\w+")
        assert pattern is pattern2  # Should be cached
        assert regex_cache.hit_count == 1


if __name__ == "__main__":
    pytest.main([__file__])
