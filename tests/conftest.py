"""Pytest configuration and shared fixtures for cespy tests."""

import sys
from pathlib import Path

import pytest

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def test_files_dir() -> Path:
    """Return the path to the test files directory."""
    return Path(__file__).parent / "testfiles"


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Return a temporary directory for test output."""
    return tmp_path


@pytest.fixture
def sample_netlist(test_files_dir: Path) -> Path:
    """Return path to a sample netlist file."""
    netlist = test_files_dir / "simple_rc.net"
    if not netlist.exists():
        # Create a simple RC circuit netlist for testing
        netlist.write_text(
            """* Simple RC Circuit
V1 in 0 1
R1 in out 1k
C1 out 0 1u
.tran 1m
.end
"""
        )
    return netlist


@pytest.fixture
def sample_asc_file(test_files_dir: Path) -> Path:
    """Return path to a sample .asc file."""
    asc_file = test_files_dir / "simple_rc.asc"
    # This would contain actual .asc content in a real test
    # For now, we'll mark it as needing implementation
    return asc_file


# Platform-specific markers
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "windows: mark test to run only on Windows"
    )
    config.addinivalue_line(
        "markers", "linux: mark test to run only on Linux"
    )
    config.addinivalue_line(
        "markers", "macos: mark test to run only on macOS"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "requires_ltspice: mark test as requiring LTSpice"
    )
    config.addinivalue_line(
        "markers", "requires_ngspice: mark test as requiring NGSpice"
    )


def pytest_collection_modifyitems(config, items):
    """Skip platform-specific tests on wrong platforms."""
    skip_windows = pytest.mark.skip(reason="Test only runs on Windows")
    skip_linux = pytest.mark.skip(reason="Test only runs on Linux")
    skip_macos = pytest.mark.skip(reason="Test only runs on macOS")

    for item in items:
        if "windows" in item.keywords and sys.platform != "win32":
            item.add_marker(skip_windows)
        elif "linux" in item.keywords and sys.platform != "linux":
            item.add_marker(skip_linux)
        elif "macos" in item.keywords and sys.platform != "darwin":
            item.add_marker(skip_macos)
