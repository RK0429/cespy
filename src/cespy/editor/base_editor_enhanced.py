#!/usr/bin/env python
# coding=utf-8
"""Enhanced base editor with common editing operations and new features.

This module extends the BaseEditor with additional functionality including:
- Undo/redo capability
- Common editing operations extracted into reusable methods
- Batch operations support
- Change tracking integration
- Validation integration
"""

import logging
import re
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from ..exceptions import ComponentNotFoundError, ParameterNotFoundError
from abc import ABC
from .base_editor import BaseEditor, Component, scan_eng, format_eng
from .circuit_validator import CircuitValidator, ValidationResult
from .component_factory import ComponentFactory, ComponentType
from .schematic_differ import SchematicDiffer, SchematicDiff

_logger = logging.getLogger("cespy.BaseEditorEnhanced")


@dataclass
class EditOperation:
    """Represents a single edit operation for undo/redo."""

    operation_type: str  # 'add', 'remove', 'modify', 'batch'
    target: str  # component ref, parameter name, or instruction
    old_value: Any = None
    new_value: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    sub_operations: List["EditOperation"] = field(default_factory=list)


class BaseEditorEnhanced(BaseEditor, ABC):
    """Enhanced base editor with additional editing capabilities.

    This class extends BaseEditor with:
    - Undo/redo functionality
    - Batch operations
    - Change tracking
    - Validation integration
    - Common editing patterns
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize enhanced editor."""
        super().__init__(*args, **kwargs)

        # Undo/redo support
        self._undo_stack: deque[EditOperation] = deque(maxlen=100)
        self._redo_stack: deque[EditOperation] = deque(maxlen=100)
        self._batch_operation: Optional[EditOperation] = None

        # Component factory and validation
        self._component_factory = ComponentFactory()
        self._validator = CircuitValidator()
        self._differ = SchematicDiffer()

        # Change tracking
        self._track_changes = False
        self._change_listeners: List[Callable[[EditOperation], None]] = []

        _logger.info("BaseEditorEnhanced initialized")

    # === Undo/Redo Support ===

    def undo(self) -> bool:
        """Undo the last operation.

        Returns:
            True if an operation was undone, False if nothing to undo
        """
        if not self._undo_stack:
            _logger.debug("Nothing to undo")
            return False

        operation = self._undo_stack.pop()
        self._apply_reverse_operation(operation)
        self._redo_stack.append(operation)

        _logger.info(
            "Undid operation: %s on %s", operation.operation_type, operation.target
        )
        return True

    def redo(self) -> bool:
        """Redo the last undone operation.

        Returns:
            True if an operation was redone, False if nothing to redo
        """
        if not self._redo_stack:
            _logger.debug("Nothing to redo")
            return False

        operation = self._redo_stack.pop()
        self._apply_operation(operation)
        self._undo_stack.append(operation)

        _logger.info(
            "Redid operation: %s on %s", operation.operation_type, operation.target
        )
        return True

    def clear_undo_history(self) -> None:
        """Clear undo/redo history."""
        self._undo_stack.clear()
        self._redo_stack.clear()
        _logger.debug("Cleared undo/redo history")

    def begin_batch(self, name: str = "Batch Operation") -> None:
        """Begin a batch operation that groups multiple edits.

        Args:
            name: Name for the batch operation
        """
        if self._batch_operation is not None:
            raise RuntimeError("Batch operation already in progress")

        self._batch_operation = EditOperation(
            operation_type="batch", target=name, sub_operations=[]
        )
        _logger.debug("Started batch operation: %s", name)

    def end_batch(self) -> None:
        """End the current batch operation."""
        if self._batch_operation is None:
            raise RuntimeError("No batch operation in progress")

        if self._batch_operation.sub_operations:
            self._record_operation(self._batch_operation)

        self._batch_operation = None
        _logger.debug("Ended batch operation")

    def cancel_batch(self) -> None:
        """Cancel the current batch operation without applying it."""
        if self._batch_operation is None:
            raise RuntimeError("No batch operation in progress")

        # Undo all operations in the batch
        for op in reversed(self._batch_operation.sub_operations):
            self._apply_reverse_operation(op)

        self._batch_operation = None
        _logger.debug("Cancelled batch operation")

    # === Common Editing Operations ===

    def replace_component_value(
        self,
        old_value: Union[str, float],
        new_value: Union[str, float],
        component_types: Optional[str] = None,
    ) -> List[str]:
        """Replace all components with a specific value.

        Args:
            old_value: Value to search for
            new_value: Value to replace with
            component_types: Component types to filter (e.g., 'R' for resistors)

        Returns:
            List of component references that were modified
        """
        modified = []
        components = self.get_components(component_types or "*")

        self.begin_batch(f"Replace value {old_value} with {new_value}")
        try:
            for comp_ref in components:
                try:
                    current_value = self.get_component_value(comp_ref)
                    if self._values_match(current_value, old_value):
                        self.set_component_value(comp_ref, new_value)
                        modified.append(comp_ref)
                except (ComponentNotFoundError, NotImplementedError):
                    continue

            self.end_batch()
        except Exception:
            self.cancel_batch()
            raise

        _logger.info("Replaced %d component values", len(modified))
        return modified

    def scale_component_values(
        self,
        scale_factor: float,
        component_types: Optional[str] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
    ) -> List[str]:
        """Scale component values by a factor.

        Args:
            scale_factor: Factor to multiply values by
            component_types: Component types to filter
            min_value: Minimum value after scaling
            max_value: Maximum value after scaling

        Returns:
            List of component references that were modified
        """

        modified = []
        components = self.get_components(component_types or "*")

        self.begin_batch(f"Scale components by {scale_factor}")
        try:
            for comp_ref in components:
                try:
                    current_str = self.get_component_value(comp_ref)
                    current_value = scan_eng(current_str)
                    new_value = current_value * scale_factor

                    # Apply limits if specified
                    if min_value is not None:
                        new_value = max(new_value, min_value)
                    if max_value is not None:
                        new_value = min(new_value, max_value)

                    self.set_component_value(comp_ref, format_eng(new_value))
                    modified.append(comp_ref)
                except (ComponentNotFoundError, ValueError, NotImplementedError):
                    continue

            self.end_batch()
        except Exception:
            self.cancel_batch()
            raise

        _logger.info("Scaled %d component values", len(modified))
        return modified

    def add_component_from_template(
        self,
        component_type: ComponentType,
        name: Optional[str] = None,
        nodes: Optional[List[str]] = None,
        **attributes: Any,
    ) -> Component:
        """Add a component using the component factory.

        Args:
            component_type: Type of component to add
            name: Component name (auto-generated if None)
            nodes: Node connections
            **attributes: Component attributes

        Returns:
            The created component
        """
        # Create component using factory
        component = self._component_factory.create_component(
            component_type=component_type, name=name, **attributes
        )

        # Set node connections if provided
        if nodes:
            pins = component.get_pins()
            for i, node in enumerate(nodes[: len(pins)]):
                component.connect_pin(pins[i], node)

        # Convert to Component object for this editor
        editor_component = Component(self, component.to_spice())
        editor_component.reference = component.get_name()

        # Add to circuit
        self.add_component(editor_component)

        return editor_component

    def find_components_by_value(
        self,
        value_pattern: str,
        component_types: Optional[str] = None,
        use_regex: bool = False,
    ) -> List[str]:
        """Find components matching a value pattern.

        Args:
            value_pattern: Value pattern to search for
            component_types: Component types to filter
            use_regex: Whether to use regex matching

        Returns:
            List of matching component references
        """

        matches = []
        components = self.get_components(component_types or "*")

        for comp_ref in components:
            try:
                value = self.get_component_value(comp_ref)

                if use_regex:
                    if re.search(value_pattern, value):
                        matches.append(comp_ref)
                else:
                    if value_pattern.lower() in value.lower():
                        matches.append(comp_ref)
            except (ComponentNotFoundError, NotImplementedError):
                continue

        return matches

    def copy_component(
        self, source_ref: str, new_ref: str, new_nodes: Optional[List[str]] = None
    ) -> Component:
        """Copy a component with a new reference.

        Args:
            source_ref: Source component reference
            new_ref: New component reference
            new_nodes: New node connections (uses source nodes if None)

        Returns:
            The new component
        """
        source = self.get_component(source_ref)

        # Create copy
        new_component = Component(self, str(source))
        new_component.reference = new_ref

        # Update nodes if provided
        if new_nodes:
            new_component.ports = new_nodes

        # Copy attributes
        new_component.attributes = source.attributes.copy()

        # Add to circuit
        self.add_component(new_component)

        return new_component

    # === Validation Integration ===

    def validate_circuit(self) -> ValidationResult:
        """Validate the current circuit.

        Returns:
            ValidationResult with any issues found
        """
        # Generate netlist content for validation
        temp_file = Path("temp_validation.net")
        try:
            self.save_netlist(temp_file)
            with open(temp_file, "r", encoding="utf-8") as f:
                netlist_content = f.read()

            result = self._validator.validate_netlist(netlist_content)

        finally:
            if temp_file.exists():
                temp_file.unlink()

        return result

    def validate_component(self, reference: str) -> ValidationResult:
        """Validate a specific component.

        Args:
            reference: Component reference

        Returns:
            ValidationResult for the component
        """
        component = self.get_component(reference)
        comp_type = reference[0]  # First character is type

        return self._validator.validate_component(
            component_type=comp_type,
            name=reference,
            value=self.get_component_value(reference),
            nodes=component.ports,
        )

    def add_model_to_validator(self, model_name: str) -> None:
        """Add a model name to the validator's known models.

        Args:
            model_name: Model name to add
        """
        self._validator.add_model_library(model_name)

    # === Change Tracking ===

    def enable_change_tracking(self) -> None:
        """Enable change tracking for diff generation."""
        self._track_changes = True
        self._snapshot_state()

    def disable_change_tracking(self) -> None:
        """Disable change tracking."""
        self._track_changes = False

    def get_changes(self) -> Optional[SchematicDiff]:
        """Get changes since change tracking was enabled.

        Returns:
            SchematicDiff or None if tracking not enabled
        """
        if not self._track_changes:
            return None

        current_state = self._capture_state()
        return self._differ.create_diff(self._baseline_state, current_state)

    def add_change_listener(self, listener: Callable[[EditOperation], None]) -> None:
        """Add a listener for change events.

        Args:
            listener: Function to call on changes
        """
        self._change_listeners.append(listener)

    def remove_change_listener(self, listener: Callable[[EditOperation], None]) -> None:
        """Remove a change listener.

        Args:
            listener: Listener to remove
        """
        if listener in self._change_listeners:
            self._change_listeners.remove(listener)

    # === Bulk Operations ===

    def update_components_batch(
        self, updates: Dict[str, Union[str, Dict[str, Any]]]
    ) -> List[str]:
        """Update multiple components in a single batch.

        Args:
            updates: Dict mapping component refs to new values or param dicts

        Returns:
            List of successfully updated components
        """
        updated = []

        self.begin_batch("Batch component update")
        try:
            for comp_ref, update in updates.items():
                try:
                    if isinstance(update, dict):
                        # Update parameters
                        self.set_component_parameters(comp_ref, **update)
                    else:
                        # Update value
                        self.set_component_value(comp_ref, update)
                    updated.append(comp_ref)
                except ComponentNotFoundError:
                    _logger.warning("Component %s not found", comp_ref)
                    continue

            self.end_batch()
        except Exception:
            self.cancel_batch()
            raise

        return updated

    def remove_components_by_type(self, component_type: str) -> List[str]:
        """Remove all components of a specific type.

        Args:
            component_type: Component type prefix (e.g., 'C' for capacitors)

        Returns:
            List of removed component references
        """
        removed = []
        components = self.get_components(component_type)

        self.begin_batch(f"Remove all {component_type} components")
        try:
            for comp_ref in components:
                self.remove_component(comp_ref)
                removed.append(comp_ref)

            self.end_batch()
        except Exception:
            self.cancel_batch()
            raise

        _logger.info("Removed %d components of type %s", len(removed), component_type)
        return removed

    # === Analysis Helpers ===

    def get_connected_components(self, node: str) -> List[str]:
        """Get all components connected to a specific node.

        Args:
            node: Node name

        Returns:
            List of component references connected to the node
        """
        connected = []

        for comp_ref in self.get_components():
            try:
                component = self.get_component(comp_ref)
                if node in component.ports:
                    connected.append(comp_ref)
            except ComponentNotFoundError:
                continue

        return connected

    def get_component_statistics(self) -> Dict[str, Any]:
        """Get statistics about components in the circuit.

        Returns:
            Dictionary with component counts and statistics
        """
        stats: Dict[str, Any] = {
            "total": 0,
            "by_type": {},
            "unique_values": set(),
            "node_count": 0,
            "subcircuit_count": 0,
        }

        all_nodes = set()

        for comp_ref in self.get_components():
            stats["total"] += 1
            comp_type = comp_ref[0]

            # Count by type
            stats["by_type"][comp_type] = stats["by_type"].get(comp_type, 0) + 1

            # Track nodes
            try:
                component = self.get_component(comp_ref)
                all_nodes.update(component.ports)
            except ComponentNotFoundError:
                continue

            # Track unique values
            try:
                value = self.get_component_value(comp_ref)
                stats["unique_values"].add(value)
            except (ComponentNotFoundError, NotImplementedError):
                pass

            # Count subcircuits
            if comp_type == "X":
                stats["subcircuit_count"] += 1

        stats["node_count"] = len(all_nodes)
        stats["unique_values"] = len(stats["unique_values"])

        return stats

    # === Private Helper Methods ===

    def _record_operation(self, operation: EditOperation) -> None:
        """Record an operation for undo/redo."""
        if self.is_read_only():
            return

        # Add to current batch if in progress
        if self._batch_operation is not None:
            self._batch_operation.sub_operations.append(operation)
        else:
            self._undo_stack.append(operation)
            self._redo_stack.clear()  # Clear redo stack on new operation

        # Notify listeners
        for listener in self._change_listeners:
            try:
                listener(operation)
            except Exception as e:
                _logger.error("Error in change listener: %s", e)

    def _apply_operation(self, operation: EditOperation) -> None:
        """Apply an edit operation."""
        if operation.operation_type == "batch":
            for sub_op in operation.sub_operations:
                self._apply_operation(sub_op)
        elif operation.operation_type == "modify":
            # Apply modification without recording
            self._apply_modification(
                operation.target, operation.new_value, operation.metadata
            )
        elif operation.operation_type == "add":
            # Re-add component/instruction
            self._apply_addition(
                operation.target, operation.new_value, operation.metadata
            )
        elif operation.operation_type == "remove":
            # Re-remove component/instruction
            self._apply_removal(operation.target, operation.metadata)

    def _apply_reverse_operation(self, operation: EditOperation) -> None:
        """Apply the reverse of an edit operation."""
        if operation.operation_type == "batch":
            for sub_op in reversed(operation.sub_operations):
                self._apply_reverse_operation(sub_op)
        elif operation.operation_type == "modify":
            # Restore old value
            self._apply_modification(
                operation.target, operation.old_value, operation.metadata
            )
        elif operation.operation_type == "add":
            # Remove what was added
            self._apply_removal(operation.target, operation.metadata)
        elif operation.operation_type == "remove":
            # Re-add what was removed
            self._apply_addition(
                operation.target, operation.old_value, operation.metadata
            )

    def _apply_modification(
        self, target: str, value: Any, metadata: Dict[str, Any]
    ) -> None:
        """Apply a modification without recording it."""
        mod_type = metadata.get("type", "component_value")

        if mod_type == "component_value":
            self.set_component_value(target, value)
        elif mod_type == "component_params":
            self.set_component_parameters(target, **value)
        elif mod_type == "parameter":
            self.set_parameter(target, value)
        elif mod_type == "model":
            self.set_element_model(target, value)

    def _apply_addition(
        self, target: str, value: Any, metadata: Dict[str, Any]
    ) -> None:
        """Apply an addition without recording it."""
        add_type = metadata.get("type", "instruction")

        if add_type == "component":
            self.add_component(value)
        elif add_type == "instruction":
            self.add_instruction(value)

    def _apply_removal(self, target: str, metadata: Dict[str, Any]) -> None:
        """Apply a removal without recording it."""
        remove_type = metadata.get("type", "component")

        if remove_type == "component":
            self.remove_component(target)
        elif remove_type == "instruction":
            self.remove_instruction(target)

    def _values_match(self, value1: str, value2: Union[str, float]) -> bool:
        """Check if two component values match."""

        if isinstance(value2, str):
            # String comparison
            return value1.lower() == value2.lower()

        # Numeric comparison
        try:
            num_value1 = scan_eng(value1)
            return abs(num_value1 - value2) < 1e-9
        except ValueError:
            return False

    def _snapshot_state(self) -> None:
        """Take a snapshot of current state for change tracking."""
        self._baseline_state = self._capture_state()

    def _capture_state(self) -> Dict[str, Any]:
        """Capture current circuit state."""
        # This is a simplified implementation
        # A full implementation would capture all circuit details
        state: Dict[str, Any] = {
            "components": {},
            "parameters": {},
            "instructions": [],
            "version": "1.0",
        }

        # Capture components
        for comp_ref in self.get_components():
            try:
                component = self.get_component(comp_ref)
                state["components"][comp_ref] = {
                    "value": self.get_component_value(comp_ref),
                    "attributes": component.attributes.copy(),
                    "ports": component.ports.copy(),
                }
            except (ComponentNotFoundError, NotImplementedError):
                continue

        # Capture parameters
        for param in self.get_all_parameter_names():
            try:
                state["parameters"][param] = self.get_parameter(param)
            except ParameterNotFoundError:
                continue

        return state

    # === Override Methods to Add Recording ===

    def _record_component_value_change(
        self, device: str, old_value: Optional[str], new_value: Union[str, int, float]
    ) -> None:
        """Record component value change for undo support.

        Call this method from concrete implementations when changing a component value.
        """
        self._record_operation(
            EditOperation(
                operation_type="modify",
                target=device,
                old_value=old_value,
                new_value=str(new_value),
                metadata={"type": "component_value"},
            )
        )

    def _record_component_parameters_change(
        self, element: str, old_params: Dict[str, Any], new_params: Dict[str, Any]
    ) -> None:
        """Record component parameters change for undo support.

        Call this method from concrete implementations when changing component parameters.
        """
        self._record_operation(
            EditOperation(
                operation_type="modify",
                target=element,
                old_value=old_params,
                new_value=new_params,
                metadata={"type": "component_params"},
            )
        )

    def _record_component_addition(self, component: Component, **kwargs: Any) -> None:
        """Record component addition for undo support.

        Call this method from concrete implementations after adding a component.
        """
        self._record_operation(
            EditOperation(
                operation_type="add",
                target=component.reference,
                new_value=component,
                metadata={"type": "component", "kwargs": kwargs},
            )
        )

    def _record_component_removal(self, designator: str, component: Component) -> None:
        """Record component removal for undo support.

        Call this method from concrete implementations before removing a component.
        """
        self._record_operation(
            EditOperation(
                operation_type="remove",
                target=designator,
                old_value=component,
                metadata={"type": "component"},
            )
        )

    def _record_instruction_addition(self, instruction: str) -> None:
        """Record instruction addition for undo support.

        Call this method from concrete implementations after adding an instruction.
        """
        self._record_operation(
            EditOperation(
                operation_type="add",
                target=instruction,
                new_value=instruction,
                metadata={"type": "instruction"},
            )
        )

    def _record_instruction_removal(self, instruction: str) -> None:
        """Record instruction removal for undo support.

        Call this method from concrete implementations before removing an instruction.
        """
        self._record_operation(
            EditOperation(
                operation_type="remove",
                target=instruction,
                old_value=instruction,
                metadata={"type": "instruction"},
            )
        )
