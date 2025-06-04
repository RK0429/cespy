#!/usr/bin/env python
# coding=utf-8
"""Schematic difference tracking and comparison.

This module provides functionality to track changes between schematic
versions and generate detailed change reports.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

_logger = logging.getLogger("cespy.SchematicDiffer")


class ChangeType(Enum):
    """Types of changes that can occur."""

    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    MOVED = "moved"
    RENAMED = "renamed"


@dataclass
class ComponentChange:
    """Represents a change to a component."""

    change_type: ChangeType
    component_name: str
    component_type: Optional[str] = None
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    attributes_changed: Dict[str, Tuple[Any, Any]] = field(default_factory=dict)
    position_change: Optional[Tuple[Tuple[float, float], Tuple[float, float]]] = None

    def describe(self) -> str:
        """Get human-readable description of change."""
        if self.change_type == ChangeType.ADDED:
            return f"Added {self.component_type} '{self.component_name}'"
        if self.change_type == ChangeType.REMOVED:
            return f"Removed {self.component_type} '{self.component_name}'"
        if self.change_type == ChangeType.MODIFIED:
            desc = f"Modified {self.component_name}:"
            if self.old_value != self.new_value:
                desc += f" value {self.old_value} -> {self.new_value}"
            for attr, (old, new) in self.attributes_changed.items():
                desc += f", {attr} {old} -> {new}"
            return desc
        if self.change_type == ChangeType.MOVED:
            if self.position_change:
                old_pos, new_pos = self.position_change
                return f"Moved {self.component_name} from {old_pos} to {new_pos}"
            return f"Moved {self.component_name}"
        if self.change_type == ChangeType.RENAMED:
            return f"Renamed component from '{self.old_value}' to '{self.new_value}'"
        return f"Unknown change to {self.component_name}"


@dataclass
class WireChange:
    """Represents a change to a wire/connection."""

    change_type: ChangeType
    start_point: Tuple[float, float]
    end_point: Tuple[float, float]
    net_name: Optional[str] = None
    old_net: Optional[str] = None
    new_net: Optional[str] = None

    def describe(self) -> str:
        """Get human-readable description of change."""
        wire_desc = f"Wire ({self.start_point} to {self.end_point})"
        if self.change_type == ChangeType.ADDED:
            return f"Added {wire_desc}"
        if self.change_type == ChangeType.REMOVED:
            return f"Removed {wire_desc}"
        if self.change_type == ChangeType.MODIFIED:
            return f"Modified {wire_desc}: net '{self.old_net}' -> '{self.new_net}'"
        return f"Unknown change to {wire_desc}"


@dataclass
class DirectiveChange:
    """Represents a change to a simulation directive."""

    change_type: ChangeType
    directive_type: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None

    def describe(self) -> str:
        """Get human-readable description of change."""
        if self.change_type == ChangeType.ADDED:
            return f"Added {self.directive_type}: {self.new_value}"
        if self.change_type == ChangeType.REMOVED:
            return f"Removed {self.directive_type}: {self.old_value}"
        if self.change_type == ChangeType.MODIFIED:
            return f"Modified {self.directive_type}: '{self.old_value}' -> '{self.new_value}'"
        return f"Unknown change to {self.directive_type}"


@dataclass
class SchematicDiff:
    """Contains all differences between two schematics."""

    component_changes: List[ComponentChange] = field(default_factory=list)
    wire_changes: List[WireChange] = field(default_factory=list)
    directive_changes: List[DirectiveChange] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_changes(self) -> int:
        """Get total number of changes."""
        return (
            len(self.component_changes)
            + len(self.wire_changes)
            + len(self.directive_changes)
        )

    @property
    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return self.total_changes > 0

    def get_summary(self) -> Dict[str, int]:
        """Get summary of changes by type."""
        summary = {
            "components_added": sum(
                1 for c in self.component_changes if c.change_type == ChangeType.ADDED
            ),
            "components_removed": sum(
                1 for c in self.component_changes if c.change_type == ChangeType.REMOVED
            ),
            "components_modified": sum(
                1
                for c in self.component_changes
                if c.change_type == ChangeType.MODIFIED
            ),
            "components_moved": sum(
                1 for c in self.component_changes if c.change_type == ChangeType.MOVED
            ),
            "wires_added": sum(
                1 for w in self.wire_changes if w.change_type == ChangeType.ADDED
            ),
            "wires_removed": sum(
                1 for w in self.wire_changes if w.change_type == ChangeType.REMOVED
            ),
            "directives_changed": len(self.directive_changes),
            "total_changes": self.total_changes,
        }
        return summary

    def generate_report(self, include_details: bool = True) -> str:
        """Generate a human-readable change report.

        Args:
            include_details: Whether to include detailed change descriptions

        Returns:
            Formatted change report
        """
        lines = ["=== Schematic Change Report ===\n"]

        # Summary
        summary = self.get_summary()
        lines.append("Summary:")
        lines.append(f"  Total changes: {summary['total_changes']}")
        lines.append(
            f"  Components: +{summary['components_added']} "
            f"-{summary['components_removed']} "
            f"~{summary['components_modified']} "
            f"↔{summary['components_moved']}"
        )
        lines.append(f"  Wires: +{summary['wires_added']} -{summary['wires_removed']}")
        lines.append(f"  Directives: {summary['directives_changed']}")
        lines.append("")

        if include_details:
            # Component changes
            if self.component_changes:
                lines.append("Component Changes:")
                for change in self.component_changes:
                    lines.append(f"  - {change.describe()}")
                lines.append("")

            # Wire changes
            if self.wire_changes:
                lines.append("Wire Changes:")
                for change in self.wire_changes:
                    lines.append(f"  - {change.describe()}")
                lines.append("")

            # Directive changes
            if self.directive_changes:
                lines.append("Directive Changes:")
                for change in self.directive_changes:
                    lines.append(f"  - {change.describe()}")
                lines.append("")

        return "\n".join(lines)


class SchematicDiffer:
    """Compares schematics and tracks changes.

    This class provides functionality to:
    - Compare two schematic versions
    - Track component, wire, and directive changes
    - Generate detailed change reports
    - Support undo/redo operations
    """

    def __init__(self) -> None:
        """Initialize schematic differ."""
        self._change_history: List[SchematicDiff] = []
        self._position_tolerance = 0.1  # Tolerance for position comparison

        _logger.info("SchematicDiffer initialized")

    def compare_components(
        self,
        old_components: Dict[str, Dict[str, Any]],
        new_components: Dict[str, Dict[str, Any]],
    ) -> List[ComponentChange]:
        """Compare component dictionaries.

        Args:
            old_components: Old component dictionary (name -> attributes)
            new_components: New component dictionary (name -> attributes)

        Returns:
            List of component changes
        """
        changes = []

        old_names = set(old_components.keys())
        new_names = set(new_components.keys())

        # Find added components
        for name in new_names - old_names:
            comp = new_components[name]
            changes.append(
                ComponentChange(
                    change_type=ChangeType.ADDED,
                    component_name=name,
                    component_type=comp.get("type"),
                    new_value=comp.get("value"),
                )
            )

        # Find removed components
        for name in old_names - new_names:
            comp = old_components[name]
            changes.append(
                ComponentChange(
                    change_type=ChangeType.REMOVED,
                    component_name=name,
                    component_type=comp.get("type"),
                    old_value=comp.get("value"),
                )
            )

        # Find modified components
        for name in old_names & new_names:
            old_comp = old_components[name]
            new_comp = new_components[name]

            # Check for changes
            attr_changes = {}
            position_change = None

            # Check value
            old_value = old_comp.get("value")
            new_value = new_comp.get("value")
            value_changed = old_value != new_value

            # Check attributes
            old_attrs = old_comp.get("attributes", {})
            new_attrs = new_comp.get("attributes", {})

            for attr in set(old_attrs.keys()) | set(new_attrs.keys()):
                old_val = old_attrs.get(attr)
                new_val = new_attrs.get(attr)
                if old_val != new_val:
                    attr_changes[attr] = (old_val, new_val)

            # Check position
            old_pos = old_comp.get("position", (0, 0))
            new_pos = new_comp.get("position", (0, 0))

            if self._positions_differ(old_pos, new_pos):
                position_change = (old_pos, new_pos)

                # Determine if moved or just modified
                if value_changed or attr_changes:
                    change_type = ChangeType.MODIFIED
                else:
                    change_type = ChangeType.MOVED
            elif value_changed or attr_changes:
                change_type = ChangeType.MODIFIED
            else:
                continue  # No changes

            changes.append(
                ComponentChange(
                    change_type=change_type,
                    component_name=name,
                    component_type=old_comp.get("type"),
                    old_value=old_value if value_changed else None,
                    new_value=new_value if value_changed else None,
                    attributes_changed=attr_changes,
                    position_change=position_change,
                )
            )

        return changes

    def compare_wires(
        self, old_wires: List[Dict[str, Any]], new_wires: List[Dict[str, Any]]
    ) -> List[WireChange]:
        """Compare wire lists.

        Args:
            old_wires: Old wire list
            new_wires: New wire list

        Returns:
            List of wire changes
        """
        changes = []

        # Create wire signatures for comparison
        def wire_signature(
            wire: Dict[str, Any]
        ) -> Tuple[Tuple[float, float], Tuple[float, float]]:
            start_data = wire.get("start", (0.0, 0.0))
            end_data = wire.get("end", (0.0, 0.0))
            start = (float(start_data[0]), float(start_data[1]))
            end = (float(end_data[0]), float(end_data[1]))
            # Normalize direction
            if start > end:
                start, end = end, start
            return (start, end)

        old_sigs = {wire_signature(w): w for w in old_wires}
        new_sigs = {wire_signature(w): w for w in new_wires}

        # Find added wires
        for sig in set(new_sigs.keys()) - set(old_sigs.keys()):
            wire = new_sigs[sig]
            changes.append(
                WireChange(
                    change_type=ChangeType.ADDED,
                    start_point=sig[0],
                    end_point=sig[1],
                    net_name=wire.get("net"),
                )
            )

        # Find removed wires
        for sig in set(old_sigs.keys()) - set(new_sigs.keys()):
            wire = old_sigs[sig]
            changes.append(
                WireChange(
                    change_type=ChangeType.REMOVED,
                    start_point=sig[0],
                    end_point=sig[1],
                    net_name=wire.get("net"),
                )
            )

        # Find modified wires (net name changes)
        for sig in set(old_sigs.keys()) & set(new_sigs.keys()):
            old_wire = old_sigs[sig]
            new_wire = new_sigs[sig]

            old_net = old_wire.get("net", "")
            new_net = new_wire.get("net", "")

            if old_net != new_net:
                changes.append(
                    WireChange(
                        change_type=ChangeType.MODIFIED,
                        start_point=sig[0],
                        end_point=sig[1],
                        old_net=old_net,
                        new_net=new_net,
                    )
                )

        return changes

    def compare_directives(
        self, old_directives: List[Dict[str, str]], new_directives: List[Dict[str, str]]
    ) -> List[DirectiveChange]:
        """Compare simulation directives.

        Args:
            old_directives: Old directive list
            new_directives: New directive list

        Returns:
            List of directive changes
        """
        changes = []

        # Group directives by type
        def group_directives(directives: List[Dict[str, Any]]) -> Dict[str, List[str]]:
            grouped: Dict[str, List[str]] = {}
            for d in directives:
                dir_type = d.get("type", "")
                if dir_type not in grouped:
                    grouped[dir_type] = []
                grouped[dir_type].append(d.get("value", ""))
            return grouped

        old_grouped = group_directives(old_directives)
        new_grouped = group_directives(new_directives)

        all_types = set(old_grouped.keys()) | set(new_grouped.keys())

        for dir_type in all_types:
            old_values = set(old_grouped.get(dir_type, []))
            new_values = set(new_grouped.get(dir_type, []))

            # Added directives
            for value in new_values - old_values:
                changes.append(
                    DirectiveChange(
                        change_type=ChangeType.ADDED,
                        directive_type=dir_type,
                        new_value=value,
                    )
                )

            # Removed directives
            for value in old_values - new_values:
                changes.append(
                    DirectiveChange(
                        change_type=ChangeType.REMOVED,
                        directive_type=dir_type,
                        old_value=value,
                    )
                )

            # For modified directives, we'd need more sophisticated comparison
            # This simple implementation treats changes as remove + add

        return changes

    def create_diff(
        self, old_schematic: Dict[str, Any], new_schematic: Dict[str, Any]
    ) -> SchematicDiff:
        """Create a complete diff between two schematics.

        Args:
            old_schematic: Old schematic data
            new_schematic: New schematic data

        Returns:
            SchematicDiff object
        """
        diff = SchematicDiff()

        # Compare components
        old_components = old_schematic.get("components", {})
        new_components = new_schematic.get("components", {})
        diff.component_changes = self.compare_components(old_components, new_components)

        # Compare wires
        old_wires = old_schematic.get("wires", [])
        new_wires = new_schematic.get("wires", [])
        diff.wire_changes = self.compare_wires(old_wires, new_wires)

        # Compare directives
        old_directives = old_schematic.get("directives", [])
        new_directives = new_schematic.get("directives", [])
        diff.directive_changes = self.compare_directives(old_directives, new_directives)

        # Add metadata
        diff.metadata["old_version"] = old_schematic.get("version", "unknown")
        diff.metadata["new_version"] = new_schematic.get("version", "unknown")
        diff.metadata["old_file"] = old_schematic.get("file_path", "unknown")
        diff.metadata["new_file"] = new_schematic.get("file_path", "unknown")

        # Store in history
        self._change_history.append(diff)

        _logger.info("Created diff with %d total changes", diff.total_changes)

        return diff

    def get_change_history(self) -> List[SchematicDiff]:
        """Get the change history.

        Returns:
            List of SchematicDiff objects
        """
        return self._change_history.copy()

    def clear_history(self) -> None:
        """Clear the change history."""
        self._change_history.clear()
        _logger.info("Cleared change history")

    def _positions_differ(
        self, pos1: Tuple[float, float], pos2: Tuple[float, float]
    ) -> bool:
        """Check if two positions are different beyond tolerance.

        Args:
            pos1: First position
            pos2: Second position

        Returns:
            True if positions differ significantly
        """
        dx = abs(pos1[0] - pos2[0])
        dy = abs(pos1[1] - pos2[1])
        return dx > self._position_tolerance or dy > self._position_tolerance
