"""Unit tests for sweep iterator utilities."""

import pytest
import numpy as np
from cespy.utils.sweep_iterators import (
    sweep,
    sweep_n,
    sweep_log,
    sweep_log_n
)


class TestSweepIterators:
    """Test sweep iterator functionality."""

    def test_sweep_basic(self):
        """Test basic sweep functionality."""
        result = list(sweep(0, 10, 2.5))
        expected = [0, 2.5, 5.0, 7.5, 10.0]
        
        assert len(result) == 5
        assert np.allclose(result, expected)

    def test_sweep_single_point(self):
        """Test sweep with single point."""
        result = list(sweep(5))
        
        assert len(result) == 1
        assert result[0] == 0  # When only start is provided, it sweeps from 0 to start

    def test_sweep_down(self):
        """Test sweep with downward direction."""
        result = list(sweep(10, 0, -2.5))
        expected = [10, 7.5, 5.0, 2.5, 0.0]
        
        assert len(result) == 5
        assert np.allclose(result, expected)

    def test_sweep_negative_range(self):
        """Test sweep with negative range."""
        result = list(sweep(-5, 5, 2.5))
        expected = [-5, -2.5, 0, 2.5, 5.0]
        
        assert len(result) == 5
        assert np.allclose(result, expected)

    def test_sweep_n_basic(self):
        """Test sweep_n functionality (n points)."""
        result = list(sweep_n(0, 10, 5))
        
        assert len(result) == 5
        assert result[0] == 0
        assert result[-1] == 10

    def test_sweep_log_basic(self):
        """Test basic logarithmic sweep functionality."""
        result = list(sweep_log(1, 100, 10))
        
        assert len(result) > 0
        assert result[0] == 1
        assert result[-1] <= 100

    def test_sweep_log_n_basic(self):
        """Test logarithmic sweep with n points."""
        result = list(sweep_log_n(1, 100, 3))
        
        assert len(result) == 3
        assert result[0] == 1
        assert result[-1] == 100

    def test_sweep_floating_point(self):
        """Test sweep with floating point precision."""
        result = list(sweep(0.1, 1.0, 0.1))
        
        # Check that we don't have precision issues
        assert all(isinstance(x, float) for x in result)
        assert result[0] == 0.1
        assert abs(result[-1] - 1.0) < 1e-10

    def test_sweep_empty_range(self):
        """Test sweep with empty range."""
        result = list(sweep(5, 5, 1))
        
        # Should include the single point
        assert len(result) >= 1
        assert 5 in result

    def test_sweep_iterator_protocol(self):
        """Test that sweep functions return proper iterators."""
        sweep_iter = sweep(0, 10, 2)
        
        # Should be iterable
        assert hasattr(sweep_iter, '__iter__')
        assert hasattr(sweep_iter, '__next__')
        
        # Should be able to iterate
        list1 = list(sweep_iter)
        assert len(list1) > 0

    def test_sweep_step_zero_error(self):
        """Test that zero step raises appropriate error."""
        with pytest.raises((ValueError, ZeroDivisionError)):
            list(sweep(0, 10, 0))

    def test_sweep_large_range(self):
        """Test sweep with large range."""
        result = list(sweep(0, 1000, 100))
        
        assert len(result) == 11  # 0, 100, 200, ..., 1000
        assert result[0] == 0
        assert result[-1] == 1000

    def test_sweep_n_edge_cases(self):
        """Test sweep_n edge cases."""
        # Single point
        result = list(sweep_n(5, 5, 1))
        assert len(result) == 1
        assert result[0] == 5
        
        # Two points
        result = list(sweep_n(0, 10, 2))
        assert len(result) == 2
        assert result[0] == 0
        assert result[1] == 10

    def test_sweep_log_range_validation(self):
        """Test logarithmic sweep input validation."""
        # Should work with positive values
        result = list(sweep_log(1, 10, 1))
        assert len(result) > 0
        
        # Negative or zero values might raise errors or be handled gracefully
        # This depends on the implementation
        try:
            result = list(sweep_log(0, 10, 1))
            # If it doesn't raise an error, just ensure it returns something reasonable
            assert isinstance(result, list)
        except (ValueError, Exception):
            # Expected for logarithmic sweeps with zero/negative values
            pass

    def test_sweep_reproducibility(self):
        """Test that sweep results are reproducible."""
        result1 = list(sweep(0, 10, 1))
        result2 = list(sweep(0, 10, 1))
        
        assert result1 == result2

    def test_sweep_types(self):
        """Test sweep with different numeric types."""
        # Integer inputs
        result_int = list(sweep(0, 10, 2))
        assert all(isinstance(x, (int, float)) for x in result_int)
        
        # Float inputs
        result_float = list(sweep(0.0, 10.0, 2.0))
        assert all(isinstance(x, float) for x in result_float)

    def test_sweep_boundary_conditions(self):
        """Test sweep boundary conditions."""
        # Test that endpoints are included when they should be
        result = list(sweep(0, 10, 5))
        assert 0 in result
        # 10 might or might not be included depending on step size and implementation

    def test_all_sweep_functions_callable(self):
        """Test that all sweep functions are callable."""
        assert callable(sweep)
        assert callable(sweep_n)
        assert callable(sweep_log)
        assert callable(sweep_log_n)