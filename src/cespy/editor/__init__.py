"""Circuit schematic and netlist editor modules.

This module provides editors for various SPICE-related file formats including
LTspice schematics (.asc), QSpice schematics (.qsch), and SPICE netlists.

It also includes advanced components for circuit manipulation:
- ComponentFactory: Create and manage circuit components
- CircuitValidator: Validate circuits for common errors
- SchematicDiffer: Track changes between schematic versions
- BaseEditorEnhanced: Enhanced base editor with undo/redo and batch operations
- NetlistOptimizer: Optimize netlists for better simulation performance
"""

from .asc_editor import AscEditor
from .base_editor_enhanced import BaseEditorEnhanced, EditOperation
from .circuit_validator import CircuitValidator, ValidationLevel, ValidationResult
from .component_factory import BaseComponent, ComponentFactory, ComponentType
from .netlist_optimizer import (
    NetlistOptimizer,
    OptimizationConfig,
    OptimizationLevel,
    OptimizationResult,
)
from .qsch_editor import QschEditor
from .schematic_differ import ChangeType, SchematicDiff, SchematicDiffer
from .spice_editor import SpiceCircuit, SpiceEditor

__all__ = [
    "AscEditor",
    "BaseComponent",
    "BaseEditorEnhanced",
    "ChangeType",
    "CircuitValidator",
    "ComponentFactory",
    "ComponentType",
    "EditOperation",
    "NetlistOptimizer",
    "OptimizationConfig",
    "OptimizationLevel",
    "OptimizationResult",
    "QschEditor",
    "SchematicDiff",
    "SchematicDiffer",
    "SpiceCircuit",
    "SpiceEditor",
    "ValidationLevel",
    "ValidationResult",
]
