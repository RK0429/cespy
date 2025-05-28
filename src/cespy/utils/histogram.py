#!/usr/bin/env python
# coding=utf-8

"""Module for creating histograms from simulation measurement data."""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union

import matplotlib.pyplot as plt
import numpy as np

from cespy.log.ltsteps import LTSpiceLogReader
from cespy.log.semi_dev_op_reader import MeasureReadingError


def read_measurement_data(log_file: Path) -> Dict[str, List[float]]:
    """Read measurement data from a log file.

    :param log_file: Path to the log file
    :return: Dictionary mapping measurement names to lists of values
    """
    try:
        log_reader = LTSpiceLogReader(log_file)
        measurements = {}

        # Extract measurement data from dataset
        for meas_name, meas_data in log_reader.dataset.items():
            values = []
            for step_data in meas_data:
                try:
                    # Try to convert to float, skip if not possible
                    value = float(step_data)
                    values.append(value)
                except (ValueError, TypeError):
                    pass
            if values:
                measurements[meas_name] = values

        return measurements

    except (OSError, IOError, MeasureReadingError) as e:
        print(f"Error reading log file: {e}")
        return {}


def create_histogram(
    data: List[float],
    title: str,
    bins: int = 50,
    output: Optional[str] = None,
    show_stats: bool = True,
) -> None:
    """Create a histogram from the data.

    :param data: List of values to plot
    :param title: Title for the histogram
    :param bins: Number of bins for the histogram
    :param output: Optional output file path
    :param show_stats: Whether to show statistics on the plot
    """
    _, ax = plt.subplots(figsize=(10, 6))

    # Create histogram
    _, _, _ = ax.hist(data, bins=bins, alpha=0.7, edgecolor="black")

    # Calculate statistics
    mean_val = np.mean(data)
    std_val = np.std(data)
    median_val = np.median(data)

    # Add vertical lines for mean and median
    ax.axvline(
        mean_val,
        color="red",
        linestyle="dashed",
        linewidth=2,
        label=f"Mean: {mean_val:.3e}",
    )
    ax.axvline(
        median_val,
        color="green",
        linestyle="dashed",
        linewidth=2,
        label=f"Median: {median_val:.3e}",
    )

    # Add title and labels
    ax.set_title(title)
    ax.set_xlabel("Value")
    ax.set_ylabel("Count")

    # Add statistics text box if requested
    if show_stats:
        stats_text = (
            f"Count: {len(data)}\nMean: {mean_val:.3e}\nStd: {std_val:.3e}\n"
            f"Min: {min(data):.3e}\nMax: {max(data):.3e}"
        )
        ax.text(
            0.7,
            0.95,
            stats_text,
            transform=ax.transAxes,
            verticalalignment="top",
            bbox={"boxstyle": "round", "facecolor": "wheat", "alpha": 0.5},
        )

    ax.legend()
    ax.grid(True, alpha=0.3)

    # Save or show
    if output:
        plt.savefig(output, dpi=150, bbox_inches="tight")
        print(f"Histogram saved to: {output}")
    else:
        plt.show()


def plot_single_measurement(
    measurements: Dict[str, List[float]], 
    measurement_name: str, 
    args: argparse.Namespace
) -> None:
    """Plot a single measurement histogram."""
    create_histogram(
        measurements[measurement_name],
        f"Histogram: {measurement_name}",
        bins=args.bins,
        output=args.output,
        show_stats=not args.no_stats,
    )


def plot_multiple_measurements(
    measurements: Dict[str, List[float]], 
    args: argparse.Namespace
) -> None:
    """Plot multiple measurements in subplots."""
    n_meas = len(measurements)
    n_cols = min(3, n_meas)
    n_rows = (n_meas + n_cols - 1) // n_cols

    _, axes = plt.subplots(n_rows, n_cols, figsize=(5 * n_cols, 4 * n_rows))
    if n_meas == 1:
        axes = [axes]
    else:
        axes = axes.flatten()

    for idx, (name, values) in enumerate(measurements.items()):
        if idx < len(axes):
            ax = axes[idx]
            ax.hist(values, bins=args.bins, edgecolor="black", alpha=0.7)
            ax.set_title(name)
            ax.set_xlabel("Value")
            ax.set_ylabel("Frequency")
            ax.grid(True, alpha=0.3)
            
            if args.no_stats:
                continue
                
            # Add statistics
            mean_val = np.mean(values)
            std_val = np.std(values)
            ax.axvline(mean_val, color="red", linestyle="--", linewidth=2)
            ax.text(
                0.02, 0.98, 
                f"μ={mean_val:.3g}\nσ={std_val:.3g}",
                transform=ax.transAxes, 
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
                verticalalignment="top",
                fontsize=10,
            )

    # Hide extra subplots
    for idx in range(n_meas, len(axes)):
        axes[idx].set_visible(False)

    plt.tight_layout()
    if args.output:
        plt.savefig(args.output, dpi=150, bbox_inches="tight")
        print(f"Histograms saved to: {args.output}")
    else:
        plt.show()


def main() -> None:
    """Command-line interface for creating histograms."""
    parser = argparse.ArgumentParser(
        description="Create histograms from SPICE simulation measurement data"
    )
    parser.add_argument(
        "log_file", type=Path, help="Path to the log file containing measurement data"
    )
    parser.add_argument(
        "-m",
        "--measurement",
        help="Specific measurement to plot (if not specified, all measurements are plotted)",
    )
    parser.add_argument(
        "-b",
        "--bins",
        type=int,
        default=50,
        help="Number of bins for the histogram (default: 50)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output file path for saving the plot (e.g., histogram.png)",
    )
    parser.add_argument(
        "--no-stats", action="store_true", help="Don't show statistics on the plot"
    )
    parser.add_argument(
        "-l", "--list", action="store_true", help="List available measurements and exit"
    )

    args = parser.parse_args()

    if not args.log_file.exists():
        print(f"Error: Log file '{args.log_file}' not found")
        sys.exit(1)

    # Read measurement data
    measurements = read_measurement_data(args.log_file)

    if not measurements:
        print("No measurement data found in log file")
        sys.exit(1)

    # List measurements if requested
    if args.list:
        print(f"Available measurements in {args.log_file.name}:")
        for name, values in measurements.items():
            print(f"  {name} ({len(values)} values)")
        sys.exit(0)

    # Plot specific measurement or all
    if args.measurement:
        if args.measurement not in measurements:
            print(f"Error: Measurement '{args.measurement}' not found in log file")
            print(f"Available measurements: {', '.join(measurements.keys())}")
            sys.exit(1)
        plot_single_measurement(measurements, args.measurement, args)
    elif len(measurements) == 1:
        # Single measurement - plot directly
        name = list(measurements.keys())[0]
        plot_single_measurement(measurements, name, args)
    else:
        # Multiple measurements - create subplots
        plot_multiple_measurements(measurements, args)


if __name__ == "__main__":
    main()
