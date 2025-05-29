"""
Centralized path utilities for cespy.

This module provides cross-platform path handling, file searching, and
simulator executable detection utilities.
"""

import os
import sys
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import List, Optional, Union, Tuple

from cespy.core.constants import Simulators, FileExtensions


def normalize_path(path: Union[str, Path]) -> str:
    """
    Normalize a path for the current platform.
    
    Args:
        path: Path to normalize
        
    Returns:
        Normalized path string
    """
    return os.path.normpath(str(path))


def join_paths(*paths: Union[str, Path]) -> str:
    """
    Join path components intelligently.
    
    Args:
        *paths: Path components to join
        
    Returns:
        Joined path string
    """
    return os.path.join(*[str(p) for p in paths])


def resolve_path(path: Union[str, Path], base_path: Optional[Union[str, Path]] = None) -> str:
    """
    Resolve a path to its absolute form.
    
    Args:
        path: Path to resolve
        base_path: Optional base path for relative resolution
        
    Returns:
        Absolute path string
    """
    path = Path(path)
    if base_path and not path.is_absolute():
        path = Path(base_path) / path
    return str(path.resolve())


def get_absolute_path(path: Union[str, Path]) -> str:
    """
    Get the absolute path, expanding user directory if needed.
    
    Args:
        path: Path to convert
        
    Returns:
        Absolute path string
    """
    return os.path.abspath(os.path.expanduser(str(path)))


# Platform detection
def get_platform() -> str:
    """Get the current platform name."""
    return sys.platform


def is_windows() -> bool:
    """Check if running on Windows."""
    return sys.platform.startswith('win')


def is_macos() -> bool:
    """Check if running on macOS."""
    return sys.platform == 'darwin'


def is_linux() -> bool:
    """Check if running on Linux."""
    return sys.platform.startswith('linux')


def is_wine_environment(exe_path: Optional[str] = None) -> bool:
    """
    Check if running under Wine or if the executable path suggests Wine.
    
    Args:
        exe_path: Optional executable path to check
        
    Returns:
        True if Wine environment detected
    """
    # Check environment variable
    if os.environ.get('WINEDEBUG') is not None:
        return True
    
    # Check if exe_path contains wine indicators
    if exe_path:
        exe_lower = str(exe_path).lower()
        if 'wine' in exe_lower or '/.wine/' in exe_lower:
            return True
            
    return False


def convert_wine_path(path: str, c_drive: Optional[str] = None) -> str:
    """
    Convert Windows path to Wine path format.
    
    Args:
        path: Windows-style path (e.g., C:\\Program Files\\...)
        c_drive: Optional custom Wine C: drive location
        
    Returns:
        Wine-compatible path
    """
    if not path:
        return path
        
    # Default Wine C: drive location
    if c_drive is None:
        c_drive = os.path.expanduser("~/.wine/drive_c")
    
    # Handle various Windows path formats
    if path.startswith("C:\\") or path.startswith("c:\\"):
        return os.path.join(c_drive, path[3:].replace("\\", "/"))
    elif path.startswith("C:/") or path.startswith("c:/"):
        return os.path.join(c_drive, path[3:])
    
    # Already a Unix path
    return path


def expand_and_check_local_dir(path: Union[str, Path], wine_c_drive: Optional[str] = None) -> Tuple[str, bool]:
    """
    Expand path and check if it exists, handling Wine paths.
    
    Args:
        path: Path to expand and check
        wine_c_drive: Optional Wine C: drive location
        
    Returns:
        Tuple of (expanded_path, exists)
    """
    path_str = str(path)
    
    # Try as-is first
    expanded = os.path.expanduser(path_str)
    if os.path.exists(expanded):
        return expanded, True
    
    # Try Wine path conversion
    if is_wine_environment() or path_str.upper().startswith("C:"):
        wine_path = convert_wine_path(path_str, wine_c_drive)
        if os.path.exists(wine_path):
            return wine_path, True
    
    return expanded, False


# File and directory operations
def find_file(filename: str, search_paths: List[Union[str, Path]]) -> Optional[str]:
    """
    Find a file in the given search paths.
    
    Args:
        filename: Name of file to find
        search_paths: List of directories to search
        
    Returns:
        Full path to file if found, None otherwise
    """
    for search_path in search_paths:
        path = Path(search_path) / filename
        if path.exists() and path.is_file():
            return str(path)
    return None


def find_executable(exe_names: List[str], search_paths: Optional[List[Union[str, Path]]] = None) -> Optional[str]:
    """
    Find an executable in system PATH or given search paths.
    
    Args:
        exe_names: List of executable names to search for
        search_paths: Optional list of directories to search
        
    Returns:
        Full path to executable if found, None otherwise
    """
    # First try system PATH
    for exe_name in exe_names:
        exe_path = shutil.which(exe_name)
        if exe_path:
            return exe_path
    
    # Then try custom search paths
    if search_paths:
        for exe_name in exe_names:
            found = find_file(exe_name, search_paths)
            if found:
                return found
                
    return None


def ensure_directory_exists(path: Union[str, Path]) -> str:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        path: Directory path
        
    Returns:
        Normalized directory path
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def is_valid_directory(path: Union[str, Path]) -> bool:
    """Check if path is a valid directory."""
    return Path(path).is_dir()


def is_valid_file(path: Union[str, Path]) -> bool:
    """Check if path is a valid file."""
    return Path(path).is_file()


# Simulator-specific paths
def get_default_simulator_paths(simulator_type: str) -> List[str]:
    """
    Get default installation paths for a simulator.
    
    Args:
        simulator_type: One of the simulator constants from Simulators
        
    Returns:
        List of typical installation paths
    """
    paths = []
    
    if simulator_type == Simulators.LTSPICE:
        if is_windows():
            paths.extend([
                r"C:\Program Files\LTC\LTspiceXVII",
                r"C:\Program Files\ADI\LTspice",
                r"C:\Program Files (x86)\LTC\LTspiceIV",
                os.path.expanduser(r"~\AppData\Local\Programs\ADI\LTspice"),
            ])
        elif is_macos():
            paths.extend([
                "/Applications/LTspice.app/Contents/MacOS",
                os.path.expanduser("~/Applications/LTspice.app/Contents/MacOS"),
            ])
        else:  # Linux
            paths.extend([
                "/usr/local/bin",
                "/usr/bin",
                os.path.expanduser("~/.wine/drive_c/Program Files/LTC/LTspiceXVII"),
                os.path.expanduser("~/.wine/drive_c/Program Files/ADI/LTspice"),
            ])
            
    elif simulator_type == Simulators.NGSPICE:
        if is_windows():
            paths.extend([
                r"C:\Spice64\bin",
                r"C:\Program Files\ngspice\bin",
                r"C:\ngspice\bin",
            ])
        else:
            paths.extend([
                "/usr/local/bin",
                "/usr/bin",
                "/opt/ngspice/bin",
            ])
            
    elif simulator_type == Simulators.QSPICE:
        if is_windows():
            paths.extend([
                r"C:\Program Files\QSPICE",
                os.path.expanduser(r"~\AppData\Local\Programs\QSPICE"),
            ])
            
    elif simulator_type == Simulators.XYCE:
        paths.extend([
            "/usr/local/bin",
            "/usr/bin",
            "/opt/xyce/bin",
            r"C:\Program Files\Xyce\bin" if is_windows() else "",
        ])
        
    return [p for p in paths if p]  # Filter out empty strings


def get_simulator_library_paths(simulator_exe: str) -> List[str]:
    """
    Get default library paths for a simulator based on its executable location.
    
    Args:
        simulator_exe: Path to simulator executable
        
    Returns:
        List of library directories
    """
    exe_dir = os.path.dirname(simulator_exe)
    parent_dir = os.path.dirname(exe_dir)
    
    paths = [
        os.path.join(parent_dir, "lib"),
        os.path.join(parent_dir, "library"),
        os.path.join(exe_dir, "lib"),
        os.path.join(exe_dir, "library"),
    ]
    
    return [p for p in paths if os.path.isdir(p)]


# Temporary file handling
def get_temp_directory() -> str:
    """Get the system temporary directory."""
    return tempfile.gettempdir()


def create_temp_directory(prefix: str = "cespy_") -> str:
    """
    Create a temporary directory.
    
    Args:
        prefix: Prefix for directory name
        
    Returns:
        Path to created directory
    """
    return tempfile.mkdtemp(prefix=prefix)


def extract_to_temp(archive_path: str, filename: str) -> Optional[str]:
    """
    Extract a file from an archive to a temporary location.
    
    Args:
        archive_path: Path to archive file
        filename: Name of file to extract
        
    Returns:
        Path to extracted file, or None if not found
    """
    if not zipfile.is_zipfile(archive_path):
        return None
        
    temp_dir = create_temp_directory()
    
    try:
        with zipfile.ZipFile(archive_path, 'r') as zf:
            if filename in zf.namelist():
                zf.extract(filename, temp_dir)
                return os.path.join(temp_dir, filename)
    except Exception:
        pass
        
    return None


def guess_process_name(exe_path: str) -> str:
    """
    Extract process name from executable path.
    
    Args:
        exe_path: Path to executable
        
    Returns:
        Process name without extension
    """
    return os.path.splitext(os.path.basename(exe_path))[0]


# Windows-specific utilities
if is_windows():
    try:
        import ctypes
        from ctypes import wintypes
        
        def get_short_path_name(long_name: str) -> str:
            """
            Get Windows short path name (8.3 format).
            
            Args:
                long_name: Long path name
                
            Returns:
                Short path name or original if conversion fails
            """
            if not os.path.exists(long_name):
                return long_name
                
            # GetShortPathNameW returns required buffer size
            buffer_size = ctypes.windll.kernel32.GetShortPathNameW(long_name, None, 0)
            if buffer_size == 0:
                return long_name
                
            output = ctypes.create_unicode_buffer(buffer_size)
            result = ctypes.windll.kernel32.GetShortPathNameW(long_name, output, buffer_size)
            
            return output.value if result else long_name
            
    except ImportError:
        def get_short_path_name(long_name: str) -> str:
            """Fallback when ctypes not available."""
            return long_name
else:
    def get_short_path_name(long_name: str) -> str:
        """Non-Windows platforms don't have short names."""
        return long_name