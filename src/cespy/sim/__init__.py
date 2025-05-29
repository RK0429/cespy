"""Simulation runner module for executing SPICE simulations."""

from .sim_runner import SimRunner

__all__ = ["SimRunner", "SimCommander", "SimBatch"]


def __getattr__(name: str):
    """Lazy imports to avoid circular dependency."""
    if name in ("SimCommander", "SimBatch"):
        from .sim_batch import SimCommander, SimBatch
        if name == "SimCommander":
            return SimCommander
        elif name == "SimBatch":
            return SimBatch
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
