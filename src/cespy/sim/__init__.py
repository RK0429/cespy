"""Simulation runner module for executing SPICE simulations."""

from typing import Any

from .sim_runner import SimRunner

# Use lazy import for SimCommander to avoid circular imports
try:
    from .sim_batch import SimCommander
except ImportError:
    SimCommander = None  # type: ignore

__all__ = ["SimRunner"]
if SimCommander is not None:
    __all__.append("SimCommander")


def __getattr__(name: str) -> Any:
    """Lazy imports to avoid circular dependency."""
    if name == "SimCommander":
        from .sim_batch import SimCommander

        return SimCommander
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
