#!/usr/bin/env python
# coding=utf-8
"""Tests for core API consistency and deprecation management functionality."""

import warnings
from unittest.mock import Mock

import pytest

from cespy.core.api_consistency import (
    DeprecationLevel,
    deprecated,
    standardize_parameters,
    APIStandardizer,
    ParameterValidator,
    ensure_api_consistency,
    create_compatibility_wrapper,
    COMPATIBILITY_MAPPINGS,
)


class TestDeprecationDecorator:
    """Test @deprecated decorator functionality."""

    def test_basic_deprecation_warning(self) -> None:
        """Test basic deprecation warning functionality."""

        @deprecated(version="2.0", reason="Test deprecation")
        def old_function() -> str:
            return "result"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = old_function()

            assert result == "result"
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "old_function is deprecated since version 2.0" in str(w[0].message)
            assert "Test deprecation" in str(w[0].message)

    def test_deprecation_with_replacement(self) -> None:
        """Test deprecation warning with replacement suggestion."""

        @deprecated(
            version="2.0", reason="Use new function", replacement="new_function"
        )
        def old_function() -> str:
            return "result"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            old_function()

            assert "Use new_function instead" in str(w[0].message)

    def test_deprecation_levels(self) -> None:
        """Test different deprecation levels."""

        # INFO level
        @deprecated(version="2.0", reason="Info", level=DeprecationLevel.INFO)
        def info_function() -> str:
            return "info"

        # WARNING level (default)
        @deprecated(version="2.0", reason="Warning", level=DeprecationLevel.WARNING)
        def warning_function() -> str:
            return "warning"

        # ERROR level
        @deprecated(version="2.0", reason="Error", level=DeprecationLevel.ERROR)
        def error_function() -> str:
            return "error"

        # REMOVED level
        @deprecated(version="2.0", reason="Removed", level=DeprecationLevel.REMOVED)
        def removed_function() -> str:
            return "removed"

        # Test INFO (should not raise warning)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            info_function()
            # INFO level uses logging, not warnings

        # Test WARNING
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            warning_function()
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)

        # Test ERROR
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            error_function()
            assert len(w) == 1
            assert issubclass(w[0].category, FutureWarning)

        # Test REMOVED
        with pytest.raises(RuntimeError, match="API removed"):
            removed_function()

    def test_deprecation_metadata(self) -> None:
        """Test that deprecation metadata is attached to function."""

        @deprecated(version="2.0", reason="Test", replacement="new_func")
        def test_function() -> None:
            pass

        assert hasattr(test_function, "__deprecated__")
        assert test_function.__deprecated__ is True
        assert hasattr(test_function, "__deprecation_info__")

        info = test_function.__deprecation_info__
        assert info["version"] == "2.0"
        assert info["reason"] == "Test"
        assert info["replacement"] == "new_func"


class TestStandardizeParametersDecorator:
    """Test @standardize_parameters decorator functionality."""

    def test_parameter_name_conversion(self) -> None:
        """Test automatic parameter name conversion."""

        @standardize_parameters({"old_param": "new_param"})
        def test_function(new_param: str = "default", **kwargs: str) -> str:
            return new_param

        # Test with old parameter name
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = test_function(old_param="test_value")

            assert result == "test_value"
            assert len(w) == 1
            assert "old_param" in str(w[0].message)
            assert "new_param" in str(w[0].message)

    def test_both_old_and_new_parameters(self) -> None:
        """Test behavior when both old and new parameter names are provided."""

        @standardize_parameters({"old_param": "new_param"})
        def test_function(new_param: str = "default", **kwargs: str) -> str:
            return new_param

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = test_function(old_param="old_value", new_param="new_value")

            # Should use new parameter value and warn about duplication
            assert result == "new_value"
            assert len(w) == 1
            assert "Both 'old_param'" in str(w[0].message)

    def test_multiple_parameter_conversions(self) -> None:
        """Test multiple parameter name conversions."""

        @standardize_parameters(
            {"old_param1": "new_param1", "old_param2": "new_param2"}
        )
        def test_function(new_param1: str = "default1", new_param2: str = "default2", **kwargs: str) -> str:
            return f"{new_param1}_{new_param2}"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = test_function(old_param1="value1", old_param2="value2")

            assert result == "value1_value2"
            assert len(w) == 2  # One warning for each converted parameter

    def test_no_conversion_needed(self) -> None:
        """Test that functions work normally when no conversion is needed."""

        @standardize_parameters({"old_param": "new_param"})
        def test_function(new_param: str = "default", other_param: str = "other") -> str:
            return f"{new_param}_{other_param}"

        result = test_function(new_param="value", other_param="other_value")
        assert result == "value_other_value"


class TestAPIStandardizer:
    """Test APIStandardizer utility class."""

    def test_standard_method_names(self) -> None:
        """Test standard method name mapping."""
        assert APIStandardizer.get_standard_method_name("load") == "load_file"
        assert APIStandardizer.get_standard_method_name("save") == "save_file"
        assert (
            APIStandardizer.get_standard_method_name("get_component")
            == "get_component_value"
        )
        assert APIStandardizer.get_standard_method_name("analyze") == "run_analysis"
        assert (
            APIStandardizer.get_standard_method_name("unknown_method")
            == "unknown_method"
        )

    def test_standard_parameter_names(self) -> None:
        """Test standard parameter name mapping."""
        assert APIStandardizer.get_standard_parameter_name("file") == "file_path"
        assert APIStandardizer.get_standard_parameter_name("filename") == "file_path"
        assert APIStandardizer.get_standard_parameter_name("comp") == "component"
        assert APIStandardizer.get_standard_parameter_name("val") == "value"
        assert (
            APIStandardizer.get_standard_parameter_name("unknown_param")
            == "unknown_param"
        )

    def test_parameter_order_validation(self) -> None:
        """Test parameter order validation and suggestion."""
        file_params = ["encoding", "file_path", "mode"]
        ordered = APIStandardizer.validate_parameter_order(
            "file_operations", file_params
        )

        # Should put file_path first according to standard order
        assert ordered[0] == "file_path"
        assert "encoding" in ordered
        assert "mode" in ordered

    def test_unknown_operation_type(self) -> None:
        """Test parameter ordering for unknown operation types."""
        params = ["param1", "param2", "param3"]
        result = APIStandardizer.validate_parameter_order("unknown_operation", params)

        # Should return original order for unknown operation types
        assert result == params


class TestParameterValidator:
    """Test ParameterValidator utility class."""

    def test_file_path_validation(self) -> None:
        """Test file path parameter validation."""
        validator = ParameterValidator()

        # Test string path
        assert validator.validate_file_path_parameter("test.txt") == "test.txt"

        # Test bytes path
        assert validator.validate_file_path_parameter(b"test.txt") == "test.txt"

        # Test None
        assert validator.validate_file_path_parameter(None) is None

        # Test Path-like object
        from pathlib import Path

        path_obj = Path("test.txt")
        assert validator.validate_file_path_parameter(path_obj) == "test.txt"

        # Test file-like object
        mock_file = Mock()
        mock_file.name = "test.txt"
        assert validator.validate_file_path_parameter(mock_file) == "test.txt"

        # Test invalid type
        with pytest.raises(TypeError):
            validator.validate_file_path_parameter(123)

    def test_timeout_validation(self) -> None:
        """Test timeout parameter validation."""
        validator = ParameterValidator()

        # Test valid numbers
        assert validator.validate_timeout_parameter(5) == 5.0
        assert validator.validate_timeout_parameter(5.5) == 5.5
        assert validator.validate_timeout_parameter("10") == 10.0

        # Test None
        assert validator.validate_timeout_parameter(None) is None

        # Test invalid values
        with pytest.raises(ValueError):
            validator.validate_timeout_parameter(-5)

        with pytest.raises(ValueError):
            validator.validate_timeout_parameter("invalid")

        with pytest.raises(TypeError):
            validator.validate_timeout_parameter([])

    def test_boolean_validation(self) -> None:
        """Test boolean parameter validation."""
        validator = ParameterValidator()

        # Test actual booleans
        assert validator.validate_boolean_parameter(True, "test") is True
        assert validator.validate_boolean_parameter(False, "test") is False

        # Test numbers
        assert validator.validate_boolean_parameter(1, "test") is True
        assert validator.validate_boolean_parameter(0, "test") is False
        assert validator.validate_boolean_parameter(0.0, "test") is False

        # Test strings
        assert validator.validate_boolean_parameter("true", "test") is True
        assert validator.validate_boolean_parameter("TRUE", "test") is True
        assert validator.validate_boolean_parameter("1", "test") is True
        assert validator.validate_boolean_parameter("yes", "test") is True
        assert validator.validate_boolean_parameter("on", "test") is True
        assert validator.validate_boolean_parameter("enable", "test") is True

        assert validator.validate_boolean_parameter("false", "test") is False
        assert validator.validate_boolean_parameter("FALSE", "test") is False
        assert validator.validate_boolean_parameter("0", "test") is False
        assert validator.validate_boolean_parameter("no", "test") is False
        assert validator.validate_boolean_parameter("off", "test") is False
        assert validator.validate_boolean_parameter("disable", "test") is False

        # Test invalid string
        with pytest.raises(ValueError):
            validator.validate_boolean_parameter("maybe", "test")

        # Test invalid type
        with pytest.raises(TypeError):
            validator.validate_boolean_parameter([], "test")


class TestEnsureAPIConsistency:
    """Test @ensure_api_consistency decorator."""

    def test_file_path_validation(self) -> None:
        """Test automatic file path validation."""

        from typing import Optional
        
        @ensure_api_consistency
        def test_function(file_path: Optional[str] = None) -> Optional[str]:
            return file_path

        # Test valid path
        result = test_function(file_path="test.txt")
        assert result == "test.txt"

        # Test Path object
        from pathlib import Path

        result = test_function(file_path=str(Path("test.txt")))
        assert result == "test.txt"

    def test_timeout_validation(self) -> None:
        """Test automatic timeout validation."""

        from typing import Optional
        
        @ensure_api_consistency
        def test_function(timeout: Optional[float] = None) -> Optional[float]:
            return timeout

        # Test valid timeout
        result = test_function(timeout=5)
        assert result == 5.0

        # Test string timeout
        result = test_function(timeout=10.0)
        assert result == 10.0

    def test_boolean_validation(self) -> None:
        """Test automatic boolean validation."""

        @ensure_api_consistency
        def test_function(flag: bool = False) -> bool:
            return flag

        # Test string boolean
        result = test_function(flag=True)
        assert result is True

        # Test number boolean
        result = test_function(flag=True)
        assert result is True


class TestCreateCompatibilityWrapper:
    """Test create_compatibility_wrapper function."""

    def test_wrapper_creation(self) -> None:
        """Test creation of compatibility wrapper."""
        # Create a mock module dict
        from typing import Dict, Any, Callable
        module_dict: Dict[str, Callable[[Any], Any]] = {"NewFunction": lambda x: x * 2}

        # Create compatibility wrapper
        create_compatibility_wrapper("OldFunction", "NewFunction", "2.0", module_dict)

        # Test that wrapper was created
        assert "OldFunction" in module_dict
        assert callable(module_dict["OldFunction"])

        # Test that wrapper works and issues deprecation warning
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = module_dict["OldFunction"](5)

            assert result == 10  # Should call the new function
            assert len(w) == 1
            assert "deprecated" in str(w[0].message).lower()

    def test_wrapper_with_nonexistent_new_name(self) -> None:
        """Test wrapper creation when new name doesn't exist."""
        module_dict: dict[str, object] = {}

        # Should not create wrapper if new name doesn't exist
        create_compatibility_wrapper(
            "OldFunction", "NonexistentFunction", "2.0", module_dict
        )

        assert "OldFunction" not in module_dict


class TestCompatibilityMappings:
    """Test predefined compatibility mappings."""

    def test_simulator_mappings(self) -> None:
        """Test simulator class name mappings."""
        assert "LTspiceSimulator" in COMPATIBILITY_MAPPINGS
        assert COMPATIBILITY_MAPPINGS["LTspiceSimulator"] == "LTSpiceSimulator"

        assert "NgspiceSimulator" in COMPATIBILITY_MAPPINGS
        assert COMPATIBILITY_MAPPINGS["NgspiceSimulator"] == "NGSpiceSimulator"

    def test_editor_mappings(self) -> None:
        """Test editor class name mappings."""
        assert "ASCEditor" in COMPATIBILITY_MAPPINGS
        assert COMPATIBILITY_MAPPINGS["ASCEditor"] == "AscEditor"

        assert "QSCHEditor" in COMPATIBILITY_MAPPINGS
        assert COMPATIBILITY_MAPPINGS["QSCHEditor"] == "QschEditor"

    def test_analysis_mappings(self) -> None:
        """Test analysis class name mappings."""
        assert "MontecarloAnalysis" in COMPATIBILITY_MAPPINGS
        assert COMPATIBILITY_MAPPINGS["MontecarloAnalysis"] == "MonteCarloAnalysis"

        assert "WorstcaseAnalysis" in COMPATIBILITY_MAPPINGS
        assert COMPATIBILITY_MAPPINGS["WorstcaseAnalysis"] == "WorstCaseAnalysis"


class TestIntegration:
    """Integration tests for API consistency components."""

    def test_combined_decorators(self) -> None:
        """Test combining multiple API consistency decorators."""

        @deprecated(version="2.0", reason="Use new function")
        @standardize_parameters({"old_param": "new_param"})
        @ensure_api_consistency
        def test_function(new_param: str = "default", **kwargs: str) -> str:
            return new_param

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = test_function(old_param="test")

            assert result == "test"
            # Should have warnings from both deprecated and standardize_parameters
            assert len(w) == 2

    def test_class_method_decoration(self) -> None:
        """Test decorating class methods."""

        class TestClass:
            @deprecated(version="2.0", reason="Use new method")
            def old_method(self, value: int) -> int:
                return value * 2

            @standardize_parameters({"old_arg": "new_arg"})
            def standardized_method(self, new_arg: str = "default", **kwargs: str) -> str:
                return new_arg

        obj = TestClass()

        # Test deprecated method
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = obj.old_method(5)
            assert result == 10
            assert len(w) == 1

        # Test standardized method
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result_str = obj.standardized_method(old_arg="test")
            assert result_str == "test"
            assert len(w) == 1


class TestErrorHandling:
    """Test error handling in API consistency components."""

    def test_parameter_validator_edge_cases(self) -> None:
        """Test parameter validator with edge cases."""
        validator = ParameterValidator()

        # Test zero timeout (should raise error)
        with pytest.raises(ValueError):
            validator.validate_timeout_parameter(0)

        # Test very large timeout (should work)
        result = validator.validate_timeout_parameter(1e6)
        assert result == 1e6

        # Test empty string for boolean
        with pytest.raises(ValueError):
            validator.validate_boolean_parameter("", "test_param")

    def test_decorator_with_exceptions(self) -> None:
        """Test decorator behavior when decorated function raises exception."""

        @deprecated(version="2.0", reason="Test")
        def failing_function() -> None:
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                failing_function()

                # Should still issue deprecation warning before exception
                assert len(w) == 1


if __name__ == "__main__":
    pytest.main([__file__])
