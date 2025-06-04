"""Advanced analysis toolkit for circuit simulations."""

from .base_analysis import (
    AnalysisResult,
    AnalysisStatus,
    BaseAnalysis,
    ParametricAnalysis,
    ProgressReporter,
    StatisticalAnalysis,
)
from .failure_modes import FailureMode
from .fast_worst_case import FastWorstCaseAnalysis
from .montecarlo import Montecarlo as MonteCarloAnalysis
from .sensitivity_analysis import QuickSensitivityAnalysis as SensitivityAnalysis
from .sim_analysis import SimAnalysis
from .tolerance_deviations import ToleranceDeviations
from .visualization import (
    AnalysisVisualizer,
    check_plotting_availability,
    create_simple_histogram,
)
from .worst_case import WorstCaseAnalysis

__all__ = [
    # Analysis classes
    "MonteCarloAnalysis",
    "WorstCaseAnalysis",
    "FastWorstCaseAnalysis",
    "SensitivityAnalysis",
    "FailureMode",
    "ToleranceDeviations",
    "SimAnalysis",
    # Enhanced base classes
    "BaseAnalysis",
    "StatisticalAnalysis",
    "ParametricAnalysis",
    "AnalysisResult",
    "AnalysisStatus",
    "ProgressReporter",
    # Visualization tools
    "AnalysisVisualizer",
    "check_plotting_availability",
    "create_simple_histogram",
]
