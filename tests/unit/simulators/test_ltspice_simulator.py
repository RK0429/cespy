"""Unit tests for LTSpice simulator functionality."""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, mock_open
from cespy.simulators.ltspice_simulator import LTspice
from cespy.sim.simulator import SpiceSimulatorError


class TestLTspiceSimulator:
    """Test LTspice simulator class functionality."""

    def test_valid_switch_validation(self):
        """Test command line switch validation."""
        # Test valid switches
        assert LTspice.valid_switch("-alt") == ["-alt"]
        assert LTspice.valid_switch("-ascii") == ["-ascii"]
        assert LTspice.valid_switch("-big") == ["-big"]
        
        # Test switch with parameter
        switches = LTspice.valid_switch("-ini", "/path/to/ltspice.ini")
        assert "-ini" in switches[0]
        assert "/path/to/ltspice.ini" in switches[1]
        
        # Test invalid switch
        with pytest.raises(ValueError, match="Invalid switch"):
            LTspice.valid_switch("-invalid")

    def test_valid_switch_formatting(self):
        """Test switch formatting and normalization."""
        # Test automatic dash addition
        assert LTspice.valid_switch("alt") == ["-alt"]
        
        # Test empty/None handling
        assert LTspice.valid_switch("") == []
        assert LTspice.valid_switch(None) == []
        assert LTspice.valid_switch("   ") == []

    def test_valid_switch_default_switches(self):
        """Test handling of default switches."""
        # Default switches should return empty list (already included)
        with patch.object(LTspice, '_default_run_switches', ["-Run", "-b"]):
            assert LTspice.valid_switch("-Run") == []
            assert LTspice.valid_switch("-b") == []

    @pytest.mark.macos
    def test_macos_native_sim_detection(self):
        """Test macOS native simulator detection."""
        # Mock macOS with native LTspice
        with patch.object(LTspice, 'spice_exe', ["/Applications/LTspice.app/Contents/MacOS/LTspice"]):
            assert LTspice.using_macos_native_sim() is True
        
        # Mock macOS with wine
        with patch.object(LTspice, 'spice_exe', ["wine", "/path/to/LTspice.exe"]):
            assert LTspice.using_macos_native_sim() is False

    @pytest.mark.macos 
    def test_macos_native_switch_restrictions(self):
        """Test that macOS native LTspice only supports batch mode."""
        with patch.object(LTspice, 'using_macos_native_sim', return_value=True):
            with pytest.raises(ValueError, match="MacOS native LTspice supports only batch mode"):
                LTspice.valid_switch("-alt")

    def test_guess_process_name(self):
        """Test process name guessing from executable path."""
        # Test Windows paths
        assert LTspice.guess_process_name("C:/Program Files/ADI/LTspice/LTspice.exe") == "LTspice.exe"
        assert LTspice.guess_process_name("/path/to/XVIIx64.exe") == "XVIIx64.exe"
        
        # Test Unix paths
        assert LTspice.guess_process_name("/Applications/LTspice.app/Contents/MacOS/LTspice") == "LTspice"

    @patch('os.path.exists')
    def test_detect_executable_windows(self, mock_exists):
        """Test executable detection on Windows."""
        mock_exists.return_value = True
        
        with patch('sys.platform', 'win32'):
            with patch.object(LTspice, '_detect_windows_executable') as mock_detect:
                LTspice.detect_executable()
                mock_detect.assert_called_once()

    @patch('os.path.exists')
    def test_detect_executable_unix(self, mock_exists):
        """Test executable detection on Unix systems."""
        mock_exists.return_value = True
        
        with patch('sys.platform', 'linux'):
            with patch.object(LTspice, '_detect_unix_executable') as mock_detect:
                LTspice.detect_executable()
                mock_detect.assert_called_once()

    @patch('os.path.exists')
    def test_windows_executable_detection(self, mock_exists):
        """Test Windows executable path detection."""
        # Mock the first path existing
        def exists_side_effect(path):
            return "AppData/Local/Programs/ADI/LTspice/LTspice.exe" in path
        
        mock_exists.side_effect = exists_side_effect
        
        with patch('os.path.expanduser') as mock_expand:
            mock_expand.side_effect = lambda x: x.replace('~', 'C:/Users/test')
            
            LTspice._detect_windows_executable()
            
            # Should find the first available executable
            assert len(LTspice.spice_exe) > 0
            assert LTspice.process_name

    @patch('os.path.exists')
    @patch('os.path.expanduser')
    @patch('os.path.expandvars')
    def test_unix_executable_detection_wine(self, mock_expandvars, mock_expanduser, mock_exists):
        """Test Unix executable detection with wine."""
        # Mock environment variables
        mock_expandvars.return_value = "testuser"
        mock_expanduser.side_effect = lambda x: x.replace('~', '/home/test')
        
        # Mock wine path existing
        def exists_side_effect(path):
            return ".wine/drive_c" in path and "LTspice" in path
        
        mock_exists.side_effect = exists_side_effect
        
        LTspice._detect_unix_executable()
        
        # Should detect wine executable
        if LTspice.spice_exe:
            assert "wine" in LTspice.spice_exe[0]

    def test_run_without_executable(self):
        """Test running simulation without executable raises error."""
        with patch.object(LTspice, 'is_available', return_value=False):
            with pytest.raises(SpiceSimulatorError, match="Simulator executable not found"):
                LTspice.run("test.net")

    @patch('cespy.sim.simulator.run_function')
    def test_run_basic_execution(self, mock_run):
        """Test basic simulation execution."""
        mock_run.return_value = 0
        
        with patch.object(LTspice, 'is_available', return_value=True):
            with patch.object(LTspice, 'spice_exe', ["/path/to/ltspice"]):
                result = LTspice.run("test.net")
                
                mock_run.assert_called_once()
                assert result == 0

    @patch('cespy.sim.simulator.run_function')
    def test_run_with_switches(self, mock_run):
        """Test simulation with command line switches."""
        mock_run.return_value = 0
        
        with patch.object(LTspice, 'is_available', return_value=True):
            with patch.object(LTspice, 'spice_exe', ["/path/to/ltspice"]):
                LTspice.run("test.net", cmd_line_switches=["-ascii", "-alt"])
                
                # Verify switches were passed
                call_args = mock_run.call_args[0][0]  # Get the command list
                assert "-ascii" in call_args
                assert "-alt" in call_args

    @pytest.mark.windows
    @patch('cespy.sim.simulator.run_function')
    def test_run_windows_path_handling(self, mock_run):
        """Test Windows path handling in simulation."""
        mock_run.return_value = 0
        
        with patch.object(LTspice, 'is_available', return_value=True):
            with patch.object(LTspice, 'spice_exe', ["C:/Program Files/ADI/LTspice/LTspice.exe"]):
                with patch('sys.platform', 'win32'):
                    LTspice.run("C:/path/to/test.net")
                    
                    call_args = mock_run.call_args[0][0]
                    assert "-Run" in call_args
                    assert "-b" in call_args
                    assert "C:/path/to/test.net" in call_args

    @pytest.mark.linux
    @patch('cespy.sim.simulator.run_function')
    def test_run_wine_path_handling(self, mock_run):
        """Test wine path handling in simulation."""
        mock_run.return_value = 0
        
        with patch.object(LTspice, 'is_available', return_value=True):
            with patch.object(LTspice, 'spice_exe', ["wine", "/path/to/ltspice.exe"]):
                with patch('sys.platform', 'linux'):
                    LTspice.run("/tmp/test.net")
                    
                    call_args = mock_run.call_args[0][0]
                    # Should prepend Z: for wine
                    assert any("Z:/tmp/test.net" in arg for arg in call_args)

    @pytest.mark.macos
    @patch('cespy.sim.simulator.run_function')
    def test_run_macos_native_restrictions(self, mock_run):
        """Test macOS native LTspice restrictions."""
        mock_run.return_value = 0
        
        with patch.object(LTspice, 'is_available', return_value=True):
            with patch.object(LTspice, 'using_macos_native_sim', return_value=True):
                with patch.object(LTspice, 'spice_exe', ["/Applications/LTspice.app/Contents/MacOS/LTspice"]):
                    # Should fail for .asc files
                    with pytest.raises(NotImplementedError, match="MacOS native LTspice cannot run simulations on '.asc' files"):
                        LTspice.run("test.asc")
                    
                    # Should work for .net files
                    LTspice.run("test.net")
                    mock_run.assert_called_once()

    def test_create_netlist_macos_native_error(self):
        """Test netlist creation error on macOS native."""
        with patch.object(LTspice, 'using_macos_native_sim', return_value=True):
            with pytest.raises(NotImplementedError, match="MacOS native LTspice does not have netlist generation"):
                LTspice.create_netlist("test.asc")

    @patch('cespy.sim.simulator.run_function')
    @patch('builtins.open', new_callable=mock_open)
    def test_run_with_exe_log(self, mock_file, mock_run):
        """Test simulation with execution logging."""
        mock_run.return_value = 0
        
        with patch.object(LTspice, 'is_available', return_value=True):
            with patch.object(LTspice, 'spice_exe', ["/path/to/ltspice"]):
                LTspice.run("test.net", exe_log=True)
                
                # Should open log file for writing
                mock_file.assert_called_once()
                assert "test.exe.log" in str(mock_file.call_args)

    def test_parameter_replacement_in_switches(self):
        """Test parameter replacement in command switches."""
        switches = LTspice.valid_switch("-I", "/custom/lib/path")
        
        # Should replace <path> placeholder
        assert any("/custom/lib/path" in switch for switch in switches)

    def test_class_attributes_initialization(self):
        """Test that class attributes are properly initialized."""
        # Test that essential class attributes exist
        assert hasattr(LTspice, 'spice_exe')
        assert hasattr(LTspice, 'process_name')
        assert hasattr(LTspice, 'ltspice_args')
        assert hasattr(LTspice, '_default_run_switches')
        
        # Test that ltspice_args contains expected switches
        assert '-alt' in LTspice.ltspice_args
        assert '-ascii' in LTspice.ltspice_args
        assert '-big' in LTspice.ltspice_args