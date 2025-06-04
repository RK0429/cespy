#!/usr/bin/env python3
"""
Run All CESPy Examples

This script runs all example files in sequence, providing a comprehensive
demonstration of CESPy capabilities.
"""

import sys
import time
import subprocess
from pathlib import Path
from typing import Tuple


def run_example(example_file: Path) -> Tuple[bool, float]:
    """Run a single example file and capture results."""
    print(f"\n{'='*60}")
    print(f"Running: {example_file}")
    print("=" * 60)

    start_time = time.time()

    try:
        # Run the example as a subprocess
        result = subprocess.run(
            [sys.executable, str(example_file)],
            capture_output=False,  # Let output go to console
            text=True,
            cwd=example_file.parent,
            timeout=300,  # 5 minute timeout per example
        )

        elapsed_time = time.time() - start_time

        if result.returncode == 0:
            print(
                f"\n✓ {example_file.name} completed successfully in {elapsed_time:.2f}s"
            )
            return True, elapsed_time
        else:
            print(
                f"\n✗ {example_file.name} failed with return code {result.returncode}"
            )
            return False, elapsed_time

    except subprocess.TimeoutExpired:
        print(f"\n⏰ {example_file.name} timed out after 5 minutes")
        return False, 300
    except (subprocess.CalledProcessError, OSError) as e:
        elapsed_time = time.time() - start_time
        print(f"\n💥 {example_file.name} crashed with error: {e}")
        return False, elapsed_time


def main() -> int:
    """Run all examples in order."""
    print("CESPy Comprehensive Example Suite")
    print("=" * 80)
    print("This will run all CESPy examples to demonstrate the full toolkit.")
    print("Each example includes error handling and cleanup.")
    print("Some examples may skip functionality if simulators are not installed.")
    print("=" * 80)

    # Get the directory containing this script
    examples_dir = Path(__file__).parent

    # Define example files in execution order
    example_files = [
        "01_basic_simulation.py",
        "02_circuit_editing.py",
        "03_analysis_toolkit.py",
        "04_data_processing.py",
        "05_batch_distributed.py",
        "06_platform_integration.py",
    ]

    # Check that all example files exist
    missing_files = []
    for filename in example_files:
        file_path = examples_dir / filename
        if not file_path.exists():
            missing_files.append(filename)

    if missing_files:
        print(f"❌ Missing example files: {missing_files}")
        print("Please ensure all example files are present.")
        return 1

    print(f"Found {len(example_files)} example files")

    # Ask for confirmation
    response = input("\nProceed with running all examples? (y/N): ").strip().lower()
    if response not in ["y", "yes"]:
        print("Examples cancelled by user.")
        return 0

    # Run examples
    start_time = time.time()
    results = []

    for filename in example_files:
        file_path = examples_dir / filename
        success, execution_time = run_example(file_path)
        results.append({"file": filename, "success": success, "time": execution_time})

    total_time = time.time() - start_time

    # Print summary
    print(f"\n{'='*80}")
    print("EXECUTION SUMMARY")
    print("=" * 80)

    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    print(f"Total examples: {len(results)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    print(f"Success rate: {len(successful)/len(results)*100:.1f}%")
    print(f"Total execution time: {total_time:.2f} seconds")

    print("\nDetailed Results:")
    for result in results:
        status = "✓" if result["success"] else "✗"
        print(f"  {status} {result['file']:<30} {result['time']:>8.2f}s")

    if failed:
        print("\nFailed Examples:")
        for result in failed:
            print(f"  - {result['file']}")
        print("\nNote: Some failures may be expected if simulators are not installed.")

    print(f"\n{'='*80}")
    print("Examples completed!")
    print("Check individual example files for detailed functionality.")
    print("See README.md for usage instructions and troubleshooting.")
    print("=" * 80)

    return 0 if len(failed) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
