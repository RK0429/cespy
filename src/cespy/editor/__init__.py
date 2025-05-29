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
from .qsch_editor import QschEditor
from .spice_editor import SpiceCircuit, SpiceEditor
from .component_factory import ComponentFactory, ComponentType, BaseComponent
from .circuit_validator import CircuitValidator, ValidationResult, ValidationLevel
from .schematic_differ import SchematicDiffer, SchematicDiff, ChangeType
from .base_editor_enhanced import BaseEditorEnhanced, EditOperation
from .netlist_optimizer import (
    NetlistOptimizer,
    OptimizationConfig,
    OptimizationLevel,
    OptimizationResult,
)

__all__ = [
    "AscEditor",
    "QschEditor",
    "SpiceCircuit",
    "SpiceEditor",
    "ComponentFactory",
    "ComponentType",
    "BaseComponent",
    "CircuitValidator",
    "ValidationResult",
    "ValidationLevel",
    "SchematicDiffer",
    "SchematicDiff",
    "ChangeType",
    "BaseEditorEnhanced",
    "EditOperation",
    "NetlistOptimizer",
    "OptimizationConfig",
    "OptimizationLevel",
    "OptimizationResult",
]
