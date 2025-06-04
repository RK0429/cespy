#!/usr/bin/env python
# coding=utf-8
"""Visualization helpers for circuit simulation analysis results.

This module provides utilities for creating plots and visualizations from
analysis results, including histograms, scatter plots, correlation matrices,
and statistical summaries.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, TYPE_CHECKING

import numpy as np

from .base_analysis import StatisticalAnalysis

_logger = logging.getLogger("cespy.Visualization")

# Optional plotting imports (graceful degradation if not available)
try:
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure

    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    plt = None  # type: ignore[assignment]

    if TYPE_CHECKING:
        from matplotlib.figure import Figure
    else:
        Figure = Any  # type: ignore[assignment,misc]
    _logger.warning("Matplotlib not available - plotting functionality disabled")

try:
    import seaborn as sns  # type: ignore[import-untyped]  # noqa: F401

    HAS_SEABORN = True
except ImportError:
    HAS_SEABORN = False


class AnalysisVisualizer:
    """Visualization helper for analysis results."""

    def __init__(self, style: str = "seaborn-v0_8", figsize: Tuple[int, int] = (10, 6)) -> None:
        """Initialize visualizer.

        Args:
            style: Matplotlib style to use
            figsize: Default figure size
        """
        if not HAS_MATPLOTLIB:
            raise ImportError("Matplotlib is required for visualization functionality")

        self.style = style
        self.figsize = figsize

        # Apply style if available
        if plt is not None:
            try:
                plt.style.use(style)
            except Exception:
                _logger.warning("Style '%s' not available, using default", style)

    def plot_histogram(
        self,
        analysis: StatisticalAnalysis,
        measurement_name: str,
        bins: Union[int, str] = "auto",
        density: bool = True,
        show_stats: bool = True,
        save_path: Optional[Union[str, Path]] = None,
        **kwargs: Any,
    ) -> Figure:
        """Create histogram plot for a measurement.

        Args:
            analysis: Analysis instance with results
            measurement_name: Name of measurement to plot
            bins: Number of bins or binning strategy
            density: Whether to normalize histogram
            show_stats: Whether to show statistics on plot
            save_path: Optional path to save figure
            **kwargs: Additional arguments for plt.hist()

        Returns:
            Matplotlib figure
        """
        if not HAS_MATPLOTLIB:
            raise ImportError("Matplotlib is required for visualization functionality")

        # Get histogram data
        counts, bin_edges = analysis.get_histogram_data(measurement_name, bins)

        if len(counts) == 0:
            raise ValueError(f"No data found for measurement '{measurement_name}'")

        # Create figure
        assert plt is not None, "matplotlib is required for visualization"
        fig, ax = plt.subplots(figsize=self.figsize)

        # Plot histogram
        ax.hist(
            bin_edges[:-1],
            bins=bin_edges.tolist(),  # Convert to list for type compatibility
            weights=counts,
            density=density,
            alpha=0.7,
            **kwargs,
        )

        # Add statistics if requested
        if show_stats:
            stats = analysis.calculate_statistics(measurement_name)
            if stats:
                # Add vertical lines for mean and std
                mean = stats["mean"]
                std = stats["std"]

                ax.axvline(mean, color="red", linestyle="--", label=f"Mean: {mean:.3e}")
                ax.axvline(
                    mean + std,
                    color="orange",
                    linestyle=":",
                    label=f"+1σ: {mean + std:.3e}",
                )
                ax.axvline(
                    mean - std,
                    color="orange",
                    linestyle=":",
                    label=f"-1σ: {mean - std:.3e}",
                )

                # Add text box with statistics
                stats_text = (
                    f"Mean: {mean:.3e}\n"
                    f"Std: {std:.3e}\n"
                    f"CV: {stats['cv']:.1%}\n"
                    f"N: {stats['count']}"
                )

                ax.text(
                    0.02,
                    0.98,
                    stats_text,
                    transform=ax.transAxes,
                    verticalalignment="top",
                    bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
                )

        # Labels and title
        ax.set_xlabel(measurement_name)
        ax.set_ylabel("Density" if density else "Count")
        ax.set_title(f"Histogram: {measurement_name}")
        ax.grid(True, alpha=0.3)

        if show_stats:
            ax.legend()

        assert plt is not None, "matplotlib is required for visualization"
        plt.tight_layout()

        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches="tight")

        return fig

    def plot_scatter_matrix(
        self,
        analysis: StatisticalAnalysis,
        measurement_names: List[str],
        show_correlation: bool = True,
        save_path: Optional[Union[str, Path]] = None,
        **kwargs: Any,
    ) -> Figure:
        """Create scatter plot matrix for multiple measurements.

        Args:
            analysis: Analysis instance with results
            measurement_names: List of measurements to plot
            show_correlation: Whether to show correlation coefficients
            save_path: Optional path to save figure
            **kwargs: Additional arguments for plotting

        Returns:
            Matplotlib figure
        """
        if not HAS_MATPLOTLIB:
            raise ImportError("Matplotlib is required for visualization functionality")

        n_measurements = len(measurement_names)
        if n_measurements < 2:
            raise ValueError("At least 2 measurements required for scatter matrix")

        # Collect data
        data_dict = {}
        for name in measurement_names:
            values = []
            for result in analysis.results:
                if result.success and name in result.measurements:
                    value = result.measurements[name]
                    if isinstance(value, (int, float)):
                        values.append(value)
                    else:
                        values.append(np.nan)
                else:
                    values.append(np.nan)
            data_dict[name] = np.array(values)

        # Create figure
        assert plt is not None, "matplotlib is required for visualization"
        fig, axes = plt.subplots(
            n_measurements,
            n_measurements,
            figsize=(3 * n_measurements, 3 * n_measurements),
        )

        if n_measurements == 1:
            axes = np.array([[axes]])
        elif n_measurements == 2:
            axes = axes.reshape(2, 2)

        # Get correlation matrix if requested
        corr_matrix = np.array([[]])
        valid_names: List[str] = []
        if show_correlation:
            corr_matrix, valid_names = analysis.get_correlation_matrix(
                measurement_names
            )

        for i, name_y in enumerate(measurement_names):
            for j, name_x in enumerate(measurement_names):
                ax = axes[i, j]

                if i == j:
                    # Diagonal: histogram
                    data = data_dict[name_x]
                    valid_data = data[~np.isnan(data)]
                    if len(valid_data) > 0:
                        ax.hist(
                            valid_data,
                            bins="auto",
                            alpha=0.7,
                            color="skyblue",
                            **kwargs,
                        )
                    ax.set_title(name_x)
                elif i < j:
                    # Upper triangle: correlation coefficient
                    if show_correlation and corr_matrix.size > 0 and valid_names:
                        # Find indices in valid names
                        try:
                            idx_x = valid_names.index(name_x)
                            idx_y = valid_names.index(name_y)
                            corr = corr_matrix[idx_y, idx_x]
                            ax.text(
                                0.5,
                                0.5,
                                f"r = {corr:.3f}",
                                transform=ax.transAxes,
                                ha="center",
                                va="center",
                                fontsize=14,
                                weight="bold",
                            )
                        except (ValueError, IndexError):
                            ax.text(
                                0.5,
                                0.5,
                                "N/A",
                                transform=ax.transAxes,
                                ha="center",
                                va="center",
                            )
                    ax.set_xlim(0, 1)
                    ax.set_ylim(0, 1)
                    ax.set_xticks([])
                    ax.set_yticks([])
                else:
                    # Lower triangle: scatter plot
                    data_x = data_dict[name_x]
                    data_y = data_dict[name_y]

                    # Remove NaN pairs
                    valid_mask = ~(np.isnan(data_x) | np.isnan(data_y))
                    data_x_valid = data_x[valid_mask]
                    data_y_valid = data_y[valid_mask]

                    if len(data_x_valid) > 0:
                        ax.scatter(
                            data_x_valid, data_y_valid, alpha=0.6, s=20, **kwargs
                        )

                # Set labels on edges
                if i == n_measurements - 1:
                    ax.set_xlabel(name_x)
                if j == 0:
                    ax.set_ylabel(name_y)

        assert plt is not None, "matplotlib is required for visualization"
        plt.tight_layout()

        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches="tight")

        return fig

    def plot_convergence(
        self,
        analysis: StatisticalAnalysis,
        measurement_name: str,
        window_size: int = 100,
        save_path: Optional[Union[str, Path]] = None,
        **kwargs: Any,
    ) -> Figure:
        """Plot convergence of statistics over simulation runs.

        Args:
            analysis: Analysis instance with results
            measurement_name: Name of measurement to analyze
            window_size: Rolling window size for statistics
            save_path: Optional path to save figure
            **kwargs: Additional plotting arguments

        Returns:
            Matplotlib figure
        """
        if not HAS_MATPLOTLIB:
            raise ImportError("Matplotlib is required for visualization functionality")

        # Collect data in order
        values = []
        run_ids = []

        for result in sorted(analysis.results, key=lambda x: x.run_id):
            if result.success and measurement_name in result.measurements:
                value = result.measurements[measurement_name]
                if isinstance(value, (int, float)):
                    values.append(value)
                    run_ids.append(result.run_id)

        if len(values) < window_size:
            raise ValueError(f"Not enough data points (need at least {window_size})")

        values_array = np.array(values)

        # Calculate rolling statistics
        n_windows = len(values) - window_size + 1
        window_means = np.zeros(n_windows)
        window_stds = np.zeros(n_windows)
        window_centers = np.zeros(n_windows)

        for i in range(n_windows):
            window_data = values_array[i : i + window_size]
            window_means[i] = np.mean(window_data)
            window_stds[i] = np.std(window_data)
            window_centers[i] = run_ids[i + window_size // 2]

        # Create figure with subplots
        assert plt is not None, "matplotlib is required for visualization"
        fig, (ax1, ax2) = plt.subplots(
            2, 1, figsize=(self.figsize[0], self.figsize[1] * 1.5)
        )

        # Plot running mean
        ax1.plot(window_centers, window_means, "b-", label="Running Mean", **kwargs)
        ax1.axhline(
            np.mean(values_array),
            color="red",
            linestyle="--",
            label=f"Final Mean: {np.mean(values_array):.3e}",
        )
        ax1.set_ylabel("Mean Value")
        ax1.set_title(f"Convergence: {measurement_name} (Window = {window_size})")
        ax1.grid(True, alpha=0.3)
        ax1.legend()

        # Plot running standard deviation
        ax2.plot(window_centers, window_stds, "g-", label="Running Std Dev", **kwargs)
        ax2.axhline(
            np.std(values_array),
            color="red",
            linestyle="--",
            label=f"Final Std: {np.std(values_array):.3e}",
        )
        ax2.set_xlabel("Run Number")
        ax2.set_ylabel("Standard Deviation")
        ax2.grid(True, alpha=0.3)
        ax2.legend()

        assert plt is not None, "matplotlib is required for visualization"
        plt.tight_layout()

        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches="tight")

        return fig

    def plot_parameter_sensitivity(
        self,
        analysis: Any,  # Parametric analysis
        parameter_name: str,
        measurement_name: str,
        save_path: Optional[Union[str, Path]] = None,
        **kwargs: Any,
    ) -> Figure:
        """Plot measurement vs parameter for sensitivity analysis.

        Args:
            analysis: Parametric analysis instance
            parameter_name: Name of parameter to plot
            measurement_name: Name of measurement to plot
            save_path: Optional path to save figure
            **kwargs: Additional plotting arguments

        Returns:
            Matplotlib figure
        """
        if not HAS_MATPLOTLIB:
            raise ImportError("Matplotlib is required for visualization functionality")

        # Collect data
        param_values = []
        meas_values = []

        for result in analysis.results:
            if (
                result.success
                and parameter_name in result.parameters
                and measurement_name in result.measurements
            ):
                param_val = result.parameters[parameter_name]
                meas_val = result.measurements[measurement_name]

                if isinstance(param_val, (int, float)) and isinstance(
                    meas_val, (int, float)
                ):
                    param_values.append(param_val)
                    meas_values.append(meas_val)

        if not param_values:
            raise ValueError(
                f"No data found for parameter '{parameter_name}' "
                f"and measurement '{measurement_name}'"
            )

        param_array = np.array(param_values)
        meas_array = np.array(meas_values)

        # Create figure
        assert plt is not None, "matplotlib is required for visualization"
        fig, ax = plt.subplots(figsize=self.figsize)

        # Scatter plot
        ax.scatter(param_array, meas_array, alpha=0.6, **kwargs)

        # Add trend line if enough points
        if len(param_values) > 2:
            coeffs = np.polyfit(param_array, meas_array, 1)
            trend_line = np.poly1d(coeffs)
            x_trend = np.linspace(param_array.min(), param_array.max(), 100)
            y_trend = trend_line(x_trend)
            ax.plot(x_trend, y_trend, "r--", alpha=0.8, label=f"Slope: {coeffs[0]:.3e}")

        # Calculate sensitivity
        if hasattr(analysis, "get_parameter_sensitivity"):
            sensitivity = analysis.get_parameter_sensitivity(
                parameter_name, measurement_name
            )
            ax.text(
                0.02,
                0.98,
                f"Sensitivity: {sensitivity:.3f}",
                transform=ax.transAxes,
                verticalalignment="top",
                bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
            )

        ax.set_xlabel(parameter_name)
        ax.set_ylabel(measurement_name)
        ax.set_title(f"Sensitivity: {measurement_name} vs {parameter_name}")
        ax.grid(True, alpha=0.3)

        if len(param_values) > 2:
            ax.legend()

        assert plt is not None, "matplotlib is required for visualization"
        plt.tight_layout()

        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches="tight")

        return fig

    def create_analysis_report(
        self,
        analysis: StatisticalAnalysis,
        measurement_names: List[str],
        output_dir: Union[str, Path],
        report_name: str = "analysis_report",
    ) -> Path:
        """Create a comprehensive analysis report with multiple plots.

        Args:
            analysis: Analysis instance
            measurement_names: List of measurements to include
            output_dir: Directory to save report files
            report_name: Base name for report files

        Returns:
            Path to the main report file
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        report_files = []

        # Create individual histograms
        for measurement in measurement_names:
            try:
                fig = self.plot_histogram(analysis, measurement, show_stats=True)
                file_path = output_path / f"{report_name}_{measurement}_histogram.png"
                fig.savefig(file_path, dpi=300, bbox_inches="tight")
                assert plt is not None, "matplotlib is required for visualization"
                plt.close(fig)
                report_files.append(file_path)
            except Exception as e:
                _logger.warning("Failed to create histogram for %s: %s", measurement, e)

        # Create scatter matrix if multiple measurements
        if len(measurement_names) > 1:
            try:
                fig = self.plot_scatter_matrix(
                    analysis, measurement_names, show_correlation=True
                )
                file_path = output_path / f"{report_name}_scatter_matrix.png"
                fig.savefig(file_path, dpi=300, bbox_inches="tight")
                assert plt is not None, "matplotlib is required for visualization"
                plt.close(fig)
                report_files.append(file_path)
            except Exception as e:
                _logger.warning("Failed to create scatter matrix: %s", e)

        # Create convergence plots if enough data
        for measurement in measurement_names:
            if len(analysis.results) >= 100:
                try:
                    fig = self.plot_convergence(analysis, measurement, window_size=50)
                    file_path = (
                        output_path / f"{report_name}_{measurement}_convergence.png"
                    )
                    fig.savefig(file_path, dpi=300, bbox_inches="tight")
                    assert plt is not None, "matplotlib is required for visualization"
                    plt.close(fig)
                    report_files.append(file_path)
                except Exception as e:
                    _logger.warning(
                        "Failed to create convergence plot for %s: %s", measurement, e
                    )

        # Create summary statistics file
        stats_file = output_path / f"{report_name}_statistics.txt"
        with open(stats_file, "w") as f:
            f.write(f"Analysis Report: {report_name}\n")
            f.write("=" * 50 + "\n\n")

            # Overall statistics
            overall_stats = analysis.get_statistics()
            f.write("Overall Statistics:\n")
            f.write("-" * 20 + "\n")
            for key, value in overall_stats.items():
                f.write(f"{key}: {value}\n")
            f.write("\n")

            # Per-measurement statistics
            for measurement in measurement_names:
                stats = analysis.calculate_statistics(measurement)
                if stats:
                    f.write(f"Statistics for {measurement}:\n")
                    f.write("-" * 30 + "\n")
                    for key, value in stats.items():
                        if isinstance(value, float):
                            f.write(f"{key}: {value:.6e}\n")
                        else:
                            f.write(f"{key}: {value}\n")
                    f.write("\n")

        report_files.append(stats_file)

        # Create index file
        index_file = output_path / f"{report_name}_index.html"
        with open(index_file, "w") as f:
            f.write(
                f"""
<!DOCTYPE html>
<html>
<head>
    <title>Analysis Report: {report_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .plot {{ margin: 20px 0; text-align: center; }}
        img {{ max-width: 800px; border: 1px solid #ccc; }}
        .stats {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>Analysis Report: {report_name}</h1>
    <h2>Generated Files:</h2>
    <ul>
"""
            )
            for file_path in report_files:
                if file_path.suffix == ".png":
                    f.write(
                        f'        <li><a href="{file_path.name}">📊 {file_path.name}</a></li>\n'
                    )
                else:
                    f.write(
                        f'        <li><a href="{file_path.name}">📄 {file_path.name}</a></li>\n'
                    )

            f.write("    </ul>\n</body>\n</html>")

        _logger.info(
            "Analysis report created with %d files in %s",
            len(report_files),
            output_path,
        )
        return index_file


def check_plotting_availability() -> Dict[str, bool]:
    """Check availability of plotting libraries.

    Returns:
        Dictionary with library availability status
    """
    return {
        "matplotlib": HAS_MATPLOTLIB,
        "seaborn": HAS_SEABORN,
    }


def create_simple_histogram(
    values: List[float], title: str = "Histogram"
) -> Optional[Figure]:
    """Create a simple histogram without analysis dependencies.

    Args:
        values: List of values to plot
        title: Plot title

    Returns:
        Matplotlib figure or None if matplotlib unavailable
    """
    if not HAS_MATPLOTLIB:
        _logger.error("Matplotlib not available for plotting")
        return None

    assert plt is not None, "matplotlib is required for visualization"
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.hist(values, bins="auto", alpha=0.7, color="skyblue")
    ax.set_title(title)
    ax.set_xlabel("Value")
    ax.set_ylabel("Frequency")
    ax.grid(True, alpha=0.3)
    assert plt is not None, "matplotlib is required for visualization"
    plt.tight_layout()

    return fig
