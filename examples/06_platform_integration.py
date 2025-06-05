#!/usr/bin/env python3
"""
Platform Integration and Compatibility Examples

This example demonstrates cross-platform compatibility, simulator detection,
API migration, and integration with different operating systems and environments.
"""

import multiprocessing
import os
import platform
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Add the cespy package to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cespy import LTspice, NGspiceSimulator, Qspice, XyceSimulator  # noqa: E402
from cespy.utils.detect_encoding import detect_encoding  # noqa: E402


def example_platform_detection() -> None:
    """Demonstrate platform detection and system information."""
    print("=== Platform Detection Example ===")

    try:
        # Get basic platform information
        print("System Information:")
        print(f"  Operating System: {platform.system()}")
        print(f"  OS Version: {platform.version()}")
        print(f"  Architecture: {platform.machine()}")
        print(f"  Python Version: {platform.python_version()}")
        print(f"  Processor: {platform.processor()}")

        # Detect platform-specific characteristics
        is_windows = platform.system() == "Windows"
        is_macos = platform.system() == "Darwin"
        is_linux = platform.system() == "Linux"

        print("\nPlatform Flags:")
        print(f"  Windows: {is_windows}")
        print(f"  macOS: {is_macos}")
        print(f"  Linux: {is_linux}")

        # Check for 64-bit vs 32-bit
        is_64bit = platform.machine().endswith("64")
        print(f"  64-bit: {is_64bit}")

        # Environment variables
        print("\nEnvironment Information:")
        print(f"  PATH entries: {len(os.environ.get('PATH', '').split(os.pathsep))}")
        print(f"  HOME/USERPROFILE: {os.path.expanduser('~')}")
        print(f"  Temp directory: {Path.cwd()}")

        # Python-specific platform info
        print("\nPython Platform Details:")
        print(f"  Platform: {platform.platform()}")
        print(f"  Architecture tuple: {platform.architecture()}")
        print(f"  Executable: {sys.executable}")

    except (IOError, OSError, ValueError) as e:
        print(f"Error in platform detection: {e}")


def example_simulator_detection() -> Dict[str, Any]:
    """Demonstrate automatic simulator detection across platforms."""
    print("\n=== Simulator Detection Example ===")

    # Common simulator installation paths by platform
    simulator_paths = {
        "Windows": {
            "ltspice": [
                r"C:\Program Files\LTC\LTspiceXVII\XVIIx64.exe",
                r"C:\Program Files\LTC\LTspiceXVII\XVIIx86.exe",
                r"C:\Program Files (x86)\LTC\LTspiceIV\scad3.exe",
                r"C:\Users\%USERNAME%\AppData\Local\Programs\ADI\LTspice\LTspice.exe",
            ],
            "ngspice": [
                r"C:\Program Files\ngspice\bin\ngspice.exe",
                r"C:\Program Files (x86)\ngspice\bin\ngspice.exe",
                r"C:\ngspice\bin\ngspice.exe",
            ],
            "qspice": [
                r"C:\Program Files\QORVO\QSPICE\QSPICE.exe",
                r"C:\Program Files (x86)\QORVO\QSPICE\QSPICE.exe",
            ],
            "xyce": [r"C:\Program Files\Xyce\bin\Xyce.exe", r"C:\Xyce\bin\Xyce.exe"],
        },
        "Darwin": {  # macOS
            "ltspice": [
                "/Applications/LTspice.app/Contents/MacOS/LTspice",
                "/Applications/LTSpice.app/Contents/MacOS/LTSpice",
                "/usr/local/bin/ltspice",
            ],
            "ngspice": [
                "/usr/local/bin/ngspice",
                "/opt/homebrew/bin/ngspice",
                "/usr/bin/ngspice",
            ],
            "qspice": [
                "/Applications/QSPICE.app/Contents/MacOS/QSPICE",
                "/usr/local/bin/qspice",
            ],
            "xyce": ["/usr/local/bin/Xyce", "/opt/homebrew/bin/Xyce", "/usr/bin/Xyce"],
        },
        "Linux": {
            "ltspice": [
                "/usr/local/bin/ltspice",
                "/usr/bin/ltspice",
                "/opt/ltspice/ltspice",
            ],
            "ngspice": [
                "/usr/bin/ngspice",
                "/usr/local/bin/ngspice",
                "/opt/ngspice/bin/ngspice",
            ],
            "qspice": ["/usr/local/bin/qspice", "/usr/bin/qspice"],
            "xyce": ["/usr/bin/Xyce", "/usr/local/bin/Xyce", "/opt/xyce/bin/Xyce"],
        },
    }

    try:
        current_platform = platform.system()
        print(f"Detecting simulators on {current_platform}...")

        detected_simulators = {}

        if current_platform in simulator_paths:
            platform_paths = simulator_paths[current_platform]

            for simulator, paths in platform_paths.items():
                print(f"\n  Checking {simulator.upper()}:")
                found_path = None

                for path in paths:
                    # Expand environment variables on Windows
                    if current_platform == "Windows":
                        expanded_path = os.path.expandvars(path)
                    else:
                        expanded_path = path

                    if Path(expanded_path).exists():
                        found_path = expanded_path
                        print(f"    ✓ Found at: {found_path}")
                        break
                    else:
                        print(f"    ✗ Not found: {expanded_path}")

                # Also check PATH
                executable_name = simulator
                if current_platform == "Windows":
                    executable_name += ".exe"

                path_location = shutil.which(executable_name)
                if path_location and not found_path:
                    found_path = path_location
                    print(f"    ✓ Found in PATH: {found_path}")
                elif not found_path:
                    print("    ✗ Not found in PATH")

                detected_simulators[simulator] = found_path

        # Initialize simulators with detected paths
        print("\nInitializing simulators...")

        available_simulators: Dict[str, Any] = {}

        # LTSpice
        try:
            if detected_simulators.get("ltspice"):
                ltspice_sim = LTspice()
                # Optionally set custom path:
                # ltspice_sim.set_executable_path(detected_simulators['ltspice'])
                available_simulators["LTSpice"] = ltspice_sim
                print("  ✓ LTSpice initialized")
            else:
                print("  ✗ LTSpice not available")
        except (IOError, OSError, ValueError) as e:
            print(f"  ✗ LTSpice initialization failed: {e}")

        # NGSpice
        try:
            if detected_simulators.get("ngspice"):
                ngspice_sim = NGspiceSimulator()
                available_simulators["NGSpice"] = ngspice_sim
                print("  ✓ NGSpice initialized")
            else:
                print("  ✗ NGSpice not available")
        except (IOError, OSError, ValueError) as e:
            print(f"  ✗ NGSpice initialization failed: {e}")

        # QSpice
        try:
            if detected_simulators.get("qspice"):
                qspice_sim = Qspice()
                available_simulators["QSpice"] = qspice_sim
                print("  ✓ QSpice initialized")
            else:
                print("  ✗ QSpice not available")
        except (IOError, OSError, ValueError) as e:
            print(f"  ✗ QSpice initialization failed: {e}")

        # Xyce
        try:
            if detected_simulators.get("xyce"):
                xyce_sim = XyceSimulator()
                available_simulators["Xyce"] = xyce_sim
                print("  ✓ Xyce initialized")
            else:
                print("  ✗ Xyce not available")
        except (IOError, OSError, ValueError) as e:
            print(f"  ✗ Xyce initialization failed: {e}")

        print(f"\nSummary: {len(available_simulators)} simulators available")
        for name in available_simulators:
            print(f"  - {name}")

        # Note: This function was meant to return simulators for demo
        return available_simulators

    except (IOError, OSError, ValueError) as e:
        print(f"Error in simulator detection: {e}")
        return {}


def example_file_encoding_handling() -> None:
    """Demonstrate cross-platform file encoding handling."""
    print("\n=== File Encoding Handling Example ===")

    try:
        # Create test files with different encodings
        test_files = []

        # UTF-8 file (common on Linux/macOS)
        utf8_content = """* UTF-8 encoded circuit file
* Test with special characters: αβγ δεζ
V1 vin 0 DC 5
R1 vin vout 1k
.op
.end
"""
        utf8_path = Path("test_utf8.net")
        with open(utf8_path, "w", encoding="utf-8") as f:
            f.write(utf8_content)
        test_files.append(utf8_path)

        # Windows-1252 file (common on Windows)
        windows_content = """* Windows-1252 encoded circuit file
* Test with Windows characters
V1 vin 0 DC 5
R1 vin vout 1k
.op
.end
"""
        windows_path = Path("test_windows.net")
        with open(windows_path, "w", encoding="windows-1252") as f:
            f.write(windows_content)
        test_files.append(windows_path)

        # ASCII file (most compatible)
        ascii_content = """* ASCII encoded circuit file
* No special characters
V1 vin 0 DC 5
R1 vin vout 1k
.op
.end
"""
        ascii_path = Path("test_ascii.net")
        with open(ascii_path, "w", encoding="ascii") as f:
            f.write(ascii_content)
        test_files.append(ascii_path)

        print("Testing encoding detection...")

        # Test encoding detection
        for file_path in test_files:
            detected_encoding = detect_encoding(str(file_path))
            print(f"  {file_path.name}: {detected_encoding}")

            # Try to read with detected encoding
            try:
                with open(file_path, "r", encoding=detected_encoding) as f:
                    content = f.read()
                    lines = len(content.splitlines())
                    print(f"    ✓ Successfully read {lines} lines")
            except (IOError, OSError, ValueError) as e:
                print(f"    ✗ Failed to read: {e}")

        # Test robust reading function
        print("\nTesting robust file reading...")

        def read_file_robust(file_path: Path) -> Tuple[str, str]:
            """Robust file reading with encoding fallbacks."""
            encodings_to_try = ["utf-8", "windows-1252", "ascii", "latin1"]

            for encoding in encodings_to_try:
                try:
                    with open(file_path, "r", encoding=encoding) as f:
                        return f.read(), encoding
                except UnicodeDecodeError:
                    continue

            # Last resort: read as binary and decode with errors='ignore'
            with open(file_path, "rb") as f:
                binary_content = f.read()
                return binary_content.decode("utf-8", errors="ignore"), "utf-8-ignore"

        for file_path in test_files:
            content, used_encoding = read_file_robust(file_path)
            print(f"  {file_path.name}: read with {used_encoding}")
            print(f"    Content preview: {content[:50].replace(chr(10), ' ')}...")

    except (IOError, OSError, ValueError) as e:
        print(f"Error in encoding handling: {e}")
    finally:
        # Cleanup
        if "test_files" in locals():
            for file_path in test_files:
                if file_path.exists():
                    file_path.unlink()


def example_path_handling() -> None:
    """Demonstrate cross-platform path handling."""
    print("\n=== Cross-Platform Path Handling Example ===")

    try:
        print("Path handling examples:")

        # Current platform path separator
        print(f"  Path separator: '{os.sep}'")
        print(f"  Path list separator: '{os.pathsep}'")

        # Test paths with different conventions
        test_paths = [
            "circuits/amplifier.asc",  # Unix-style relative
            "circuits\\amplifier.asc",  # Windows-style relative
            "/home/user/circuits/amp.asc",  # Unix-style absolute
            "C:\\Users\\user\\circuits\\amp.asc",  # Windows-style absolute
            "~/circuits/amplifier.asc",  # Home directory relative
        ]

        print("\nNormalizing paths:")
        for path_str in test_paths:
            # Convert to Path object for normalization
            path_obj = Path(path_str)
            normalized = (
                path_obj.as_posix() if platform.system() != "Windows" else str(path_obj)
            )
            expanded = Path(path_str).expanduser()

            print(f"  Original: {path_str}")
            print(f"  Normalized: {normalized}")
            print(f"  Expanded: {expanded}")
            print()

        # Test file operations with Path objects
        print("Creating test directory structure...")

        # Create platform-appropriate directory structure
        test_dir = Path("test_platform_structure")
        test_dir.mkdir(exist_ok=True)

        subdirs = ["circuits", "results", "temp"]
        for subdir in subdirs:
            (test_dir / subdir).mkdir(exist_ok=True)
            print(f"  Created: {test_dir / subdir}")

        # Create some test files
        test_files = [
            test_dir / "circuits" / "test1.asc",
            test_dir / "circuits" / "test2.net",
            test_dir / "results" / "simulation.raw",
            test_dir / "temp" / "working.tmp",
        ]

        for file_path in test_files:
            file_path.write_text("# Test file content")
            print(f"  Created file: {file_path}")

        # Test file operations
        print("\nTesting file operations...")

        # List files recursively
        all_files = list(test_dir.rglob("*"))
        print(f"  Found {len(all_files)} items total")

        # Filter by extension
        asc_files = list(test_dir.rglob("*.asc"))
        net_files = list(test_dir.rglob("*.net"))
        print(f"  ASC files: {len(asc_files)}")
        print(f"  NET files: {len(net_files)}")

        # Get file information
        for file_path in asc_files + net_files:
            stat_info = file_path.stat()
            print(f"  {file_path.name}: {stat_info.st_size} bytes")

        # Test relative path operations
        print("\nRelative path operations:")
        base_path = test_dir / "circuits"
        for file_path in test_files[:2]:  # First two files
            relative = file_path.relative_to(test_dir)
            print(f"  {file_path.name} relative to test_dir: {relative}")

    except (IOError, OSError, ValueError) as e:
        print(f"Error in path handling: {e}")
    finally:
        # Cleanup
        if "test_dir" in locals() and test_dir.exists():
            shutil.rmtree(test_dir)
            print("Cleaned up test directory")


def example_api_compatibility() -> None:
    """Demonstrate API compatibility and migration helpers."""
    print("\n=== API Compatibility Example ===")

    try:
        print("Testing API compatibility layers...")

        # Simulate old API usage patterns
        print("\nOld-style API patterns:")

        # Old pattern: Direct simulator instantiation
        print("  Testing legacy simulator initialization...")
        try:
            # This simulates how users might have used older versions
            _ltspice_old_style = LTspice()
            print("    ✓ LTSpice (old style) - compatible")
        except (IOError, OSError, ValueError) as e:
            print(f"    ✗ LTSpice (old style) - error: {e}")

        # New pattern: Modern API
        print("  Testing modern API...")
        try:
            from cespy import simulate  # Modern unified interface  # noqa: F401

            print("    ✓ Modern unified simulate() function available")
        except ImportError:
            print("    ✗ Modern API not available")

        # Test parameter compatibility
        print("\nTesting parameter compatibility...")

        # Old-style parameter passing
        old_style_params = {
            "netlist_file": "test.net",
            "simulator_type": "ltspice",
            "output_file": "results.raw",
        }

        # New-style parameter passing
        new_style_params = {
            "circuit": "test.net",
            "simulator": LTspice(),
            "output": "results.raw",
        }

        print(f"    Old-style parameters: {list(old_style_params.keys())}")
        print(f"    New-style parameters: {list(new_style_params.keys())}")

        # API migration helper
        def migrate_parameters(
            old_params: Dict[str, Any],
        ) -> Tuple[Dict[str, Any], List[str]]:
            """Helper to migrate old parameter names to new ones."""
            migration_map = {
                "netlist_file": "circuit",
                "simulator_type": "simulator",
                "output_file": "output",
            }

            new_params = {}
            migration_warnings = []

            for old_key, value in old_params.items():
                if old_key in migration_map:
                    new_key = migration_map[old_key]
                    new_params[new_key] = value
                    migration_warnings.append(
                        f"Parameter '{old_key}' deprecated, use '{new_key}'"
                    )
                else:
                    new_params[old_key] = value

            return new_params, migration_warnings

        migrated_params, migration_warnings = migrate_parameters(old_style_params)
        print(f"    Migrated parameters: {list(migrated_params.keys())}")
        for warning in migration_warnings:
            print(f"    Warning: {warning}")

        # Test version compatibility
        print("\nTesting version compatibility...")

        # Simulate version checking
        def check_version_compatibility() -> List[str]:
            """Check if current version is compatible with user's code."""
            import cespy

            # Simulate version detection
            current_version = getattr(cespy, "__version__", "1.0.0")
            print(f"    Current CESPy version: {current_version}")

            # Define compatibility matrix
            compatible_features = {
                "1.0.0": ["basic_simulation", "ltspice_support"],
                "1.1.0": ["basic_simulation", "ltspice_support", "ngspice_support"],
                "2.0.0": [
                    "basic_simulation",
                    "ltspice_support",
                    "ngspice_support",
                    "qspice_support",
                    "analysis_toolkit",
                ],
                "2.1.0": [
                    "basic_simulation",
                    "ltspice_support",
                    "ngspice_support",
                    "qspice_support",
                    "analysis_toolkit",
                    "client_server",
                ],
            }

            # Check feature availability
            available_features = compatible_features.get(current_version, [])
            print(f"    Available features: {available_features}")

            return available_features

        _available_features = check_version_compatibility()

        # Test deprecated function warnings
        print("\nTesting deprecation warnings...")

        import warnings as warning_module

        def deprecated_function() -> str:
            """Example of a deprecated function."""
            warning_module.warn(
                "This function is deprecated and will be removed in version 3.0. "
                "Use new_function() instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            return "old_result"

        def new_function() -> str:
            """Replacement for deprecated function."""
            return "new_result"

        # Capture warnings
        with warning_module.catch_warnings(record=True) as w:
            warning_module.simplefilter("always")
            _result = deprecated_function()

            if w:
                print(f"    ✓ Deprecation warning captured: {w[0].message}")
            else:
                print(f"    ✗ No deprecation warning")

        print(f"    New function result: {new_function()}")

    except (IOError, OSError, ValueError) as e:
        print(f"Error in API compatibility: {e}")


def example_environment_configuration() -> None:
    """Demonstrate environment configuration and setup."""
    print("\n=== Environment Configuration Example ===")

    try:
        print("Environment configuration and setup...")

        # Check Python environment
        print("\nPython Environment:")
        print(f"  Python executable: {sys.executable}")
        print(f"  Python path: {sys.path[:3]}...")  # Show first 3 entries
        print(f"  Site packages: {[p for p in sys.path if 'site-packages' in p][:2]}")

        # Check required packages
        print("\nRequired packages check:")
        required_packages = ["numpy", "matplotlib", "scipy", "pandas"]

        for package in required_packages:
            try:
                __import__(package)
                print(f"  ✓ {package} available")
            except ImportError:
                print(f"  ✗ {package} not available")

        # Environment variables for simulator paths
        print("\nSimulator environment variables:")
        simulator_env_vars = [
            "LTSPICE_PATH",
            "NGSPICE_PATH",
            "QSPICE_PATH",
            "XYCE_PATH",
            "SPICE_LIB_PATH",
        ]

        for var in simulator_env_vars:
            value = os.environ.get(var, "Not set")
            print(f"  {var}: {value}")

        # Create configuration file template
        print("\nCreating configuration template...")

        config_template = """# CESPy Configuration File
# Platform: {platform}
# Generated: {timestamp}

[simulators]
# Simulator executable paths (leave empty for auto-detection)
ltspice_path =
ngspice_path =
qspice_path =
xyce_path =

[paths]
# Default directories
circuits_dir = ./circuits
results_dir = ./results
temp_dir = ./temp

[performance]
# Performance optimization settings
max_parallel_jobs = {cpu_count}
memory_limit_mb = 4096
use_temp_files = true

[compatibility]
# Compatibility settings
encoding = utf-8
path_style = {path_style}
line_endings = {line_endings}
""".format(
            platform=platform.system(),
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            cpu_count=multiprocessing.cpu_count(),
            path_style="posix" if platform.system() != "Windows" else "windows",
            line_endings="lf" if platform.system() != "Windows" else "crlf",
        )

        config_path = Path("cespy_config_template.ini")
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(config_template)
        print(f"  ✓ Configuration template created: {config_path}")

        # Test configuration loading
        print("\nTesting configuration loading...")

        try:
            import configparser

            config = configparser.ConfigParser()
            config.read(config_path)

            print(f"  Configuration sections: {list(config.sections())}")

            # Show sample configuration values
            if "performance" in config:
                max_jobs = config.get("performance", "max_parallel_jobs")
                memory_limit = config.get("performance", "memory_limit_mb")
                print(f"  Max parallel jobs: {max_jobs}")
                print(f"  Memory limit: {memory_limit} MB")

        except (IOError, OSError, ValueError) as e:
            print(f"  ✗ Configuration loading failed: {e}")

        # Setup script example
        print("\nCreating setup script example...")

        setup_script = """#!/usr/bin/env python3
'''
CESPy Environment Setup Script
Run this script to configure CESPy for your platform.
'''

import os
import sys
import platform
from pathlib import Path

def setup_cespy_environment() -> None:
    print("Setting up CESPy environment...")

    # Create default directories
    directories = ['circuits', 'results', 'temp', 'logs']
    for dir_name in directories:
        Path(dir_name).mkdir(exist_ok=True)
        print(f"  Created directory: {dir_name}")

    # Platform-specific setup
    if platform.system() == 'Windows':
        print("  Windows-specific setup...")
        # Add Windows-specific configuration
    elif platform.system() == 'Darwin':
        print("  macOS-specific setup...")
        # Add macOS-specific configuration
    elif platform.system() == 'Linux':
        print("  Linux-specific setup...")
        # Add Linux-specific configuration

    print("  Setup completed!")

if __name__ == "__main__":
    setup_cespy_environment()
"""

        setup_path = Path("setup_cespy.py")
        setup_path.write_text(setup_script)
        print(f"  ✓ Setup script created: {setup_path}")

        # Clean up template files
        config_path.unlink()
        setup_path.unlink()

    except (IOError, OSError, ValueError) as e:
        print(f"Error in environment configuration: {e}")


def main() -> None:
    """Run all platform integration examples."""
    print("CESPy Platform Integration and Compatibility Examples")
    print("=" * 90)

    # Run all platform integration examples
    example_platform_detection()
    example_simulator_detection()
    example_file_encoding_handling()
    example_path_handling()
    example_api_compatibility()
    example_environment_configuration()

    print("\n" + "=" * 90)
    print("Platform integration examples completed!")
    print("\nCapabilities demonstrated:")
    print("- Cross-platform system detection and configuration")
    print("- Automatic simulator detection and path resolution")
    print("- File encoding handling for international compatibility")
    print("- Cross-platform path and file system operations")
    print("- API compatibility and migration helpers")
    print("- Environment configuration and setup automation")
    print(
        "\nAll CESPy examples completed! Check the individual files for detailed usage."
    )


if __name__ == "__main__":
    main()
