"""Simulation runner module for executing SPICE simulations."""

from typing import Any

from .sim_runner import SimRunner

# Use lazy import for SimCommander to avoid circular imports
_sim_commander_available = False
try:
    from .sim_batch import SimCommander  # noqa: F401
    _sim_commander_available = True
except ImportError:
    pass

__all__ = ["SimRunner"]
if _sim_commander_available:
    __all__.append("SimCommander")


def __getattr__(name: str) -> Any:
    """Lazy imports to avoid circular dependency."""
    if name == "SimCommander":
        from .sim_batch import SimCommander as _SimCommander

        return _SimCommander
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
