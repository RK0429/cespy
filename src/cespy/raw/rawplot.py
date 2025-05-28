#!/usr/bin/env python
# coding=utf-8

"""Module for plotting SPICE raw waveform data."""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

import matplotlib.pyplot as plt

from cespy.raw.raw_read import RawRead


def plot_traces(
    raw_file: Path, traces: List[str], output: Optional[str] = None
) -> None:
    """Plot specified traces from a raw file.

    :param raw_file: Path to the raw file
    :param traces: List of trace names to plot
    :param output: Optional output file path for saving the plot
    """
    try:
        # Read the raw file
        raw_data = RawRead(raw_file)

        # Create figure
        fig, ax = plt.subplots(figsize=(10, 6))

        # Get the x-axis data (usually time or frequency)
        x_trace = raw_data.get_trace_names()[0]  # First trace is usually the x-axis
        x_data = raw_data.get_trace(x_trace).get_wave()

        # Plot each requested trace
        for trace_name in traces:
            try:
                trace = raw_data.get_trace(trace_name)
                y_data = trace.get_wave()

                # Handle complex data (AC analysis)
                if hasattr(y_data[0], "real"):
                    # Plot magnitude for complex data
                    import numpy as np

                    y_data = np.abs(y_data)

                ax.plot(x_data, y_data, label=trace_name)
            except KeyError:
                print(f"Warning: Trace '{trace_name}' not found in raw file")

        # Configure plot
        ax.set_xlabel(x_trace)
        ax.set_ylabel("Value")
        ax.set_title(f"Raw File: {raw_file.name}")
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Save or show plot
        if output:
            plt.savefig(output, dpi=150, bbox_inches="tight")
            print(f"Plot saved to: {output}")
        else:
            plt.show()

    except (OSError, RuntimeError, ValueError) as e:
        print(f"Error plotting raw file: {e}")
        sys.exit(1)


def main() -> None:
    """Command-line interface for plotting raw files."""
    parser = argparse.ArgumentParser(
        description="Plot traces from SPICE raw waveform files"
    )
    parser.add_argument("raw_file", type=Path, help="Path to the raw file to plot")
    parser.add_argument(
        "traces", nargs="+", help="Names of traces to plot (e.g., 'V(out)' 'I(R1)')"
    )
    parser.add_argument(
        "-o", "--output", help="Output file path for saving the plot (e.g., plot.png)"
    )
    parser.add_argument(
        "-l", "--list", action="store_true", help="List available traces and exit"
    )

    args = parser.parse_args()

    if not args.raw_file.exists():
        print(f"Error: Raw file '{args.raw_file}' not found")
        sys.exit(1)

    # List traces if requested
    if args.list:
        try:
            raw_data = RawRead(args.raw_file)
            print(f"Available traces in {args.raw_file.name}:")
            for trace_name in raw_data.get_trace_names():
                print(f"  {trace_name}")
            sys.exit(0)
        except (OSError, RuntimeError, ValueError) as e:
            print(f"Error reading raw file: {e}")
            sys.exit(1)

    # Plot the traces
    plot_traces(args.raw_file, args.traces, args.output)


if __name__ == "__main__":
    main()
