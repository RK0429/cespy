#!/usr/bin/env python
# coding=utf-8
"""Circuit validation functionality.

This module provides comprehensive validation for circuit schematics
and netlists, checking for common errors and potential simulation issues.
"""

import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from ..core import constants as core_constants
from ..core import patterns as core_patterns
from ..exceptions import InvalidComponentError, ValidationError

_logger = logging.getLogger("cespy.CircuitValidator")


class ValidationLevel(Enum):
    """Validation severity levels."""

    ERROR = "error"  # Must fix before simulation
    WARNING = "warning"  # May cause issues
    INFO = "info"  # Informational only


@dataclass
class ValidationIssue:
    """A single validation issue."""

    level: ValidationLevel
    component: Optional[str]
    message: str
    location: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of circuit validation."""

    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Check if circuit is valid (no errors)."""
        return not any(issue.level == ValidationLevel.ERROR for issue in self.issues)

    @property
    def error_count(self) -> int:
        """Get number of errors."""
        return sum(1 for issue in self.issues if issue.level == ValidationLevel.ERROR)

    @property
    def warning_count(self) -> int:
        """Get number of warnings."""
        return sum(1 for issue in self.issues if issue.level == ValidationLevel.WARNING)

    @property
    def info_count(self) -> int:
        """Get number of info messages."""
        return sum(1 for issue in self.issues if issue.level == ValidationLevel.INFO)

    def add_error(
        self,
        component: Optional[str],
        message: str,
        location: Optional[str] = None,
        suggestion: Optional[str] = None,
    ) -> None:
        """Add an error."""
        self.issues.append(
            ValidationIssue(
                level=ValidationLevel.ERROR,
                component=component,
                message=message,
                location=location,
                suggestion=suggestion,
            )
        )

    def add_warning(
        self,
        component: Optional[str],
        message: str,
        location: Optional[str] = None,
        suggestion: Optional[str] = None,
    ) -> None:
        """Add a warning."""
        self.issues.append(
            ValidationIssue(
                level=ValidationLevel.WARNING,
                component=component,
                message=message,
                location=location,
                suggestion=suggestion,
            )
        )

    def add_info(
        self, component: Optional[str], message: str, location: Optional[str] = None
    ) -> None:
        """Add an info message."""
        self.issues.append(
            ValidationIssue(
                level=ValidationLevel.INFO,
                component=component,
                message=message,
                location=location,
            )
        )

    def get_summary(self) -> str:
        """Get validation summary."""
        if self.is_valid:
            return f"Validation passed with {self.warning_count} warnings"
        else:
            return f"Validation failed: {self.error_count} errors, {self.warning_count} warnings"


class CircuitValidator:
    """Validates circuit schematics and netlists.

    This class provides comprehensive validation including:
    - Component connectivity checks
    - Value range validation
    - Model availability verification
    - Simulation directive validation
    - Common mistake detection
    """

    def __init__(self) -> None:
        """Initialize circuit validator."""
        self._model_library: Set[str] = set()
        self._custom_rules: List[Callable[..., Any]] = []
        self._known_subcircuits: Set[str] = set()

        _logger.info("CircuitValidator initialized")

    def validate_netlist(self, netlist_content: str) -> ValidationResult:
        """Validate a SPICE netlist.

        Args:
            netlist_content: SPICE netlist content

        Returns:
            Validation result
        """
        result = ValidationResult()

        # Parse netlist into components and directives
        components, directives, nodes = self._parse_netlist(netlist_content)

        # Run validation checks
        self._check_connectivity(components, nodes, result)
        self._check_component_values(components, result)
        self._check_models(components, result)
        self._check_directives(directives, result)
        self._check_common_mistakes(components, directives, result)
        self._check_custom_rules(components, directives, result)

        _logger.info("Validation complete: %s", result.get_summary())

        return result

    def validate_component(
        self, component_type: str, name: str, value: str, nodes: List[str]
    ) -> ValidationResult:
        """Validate a single component.

        Args:
            component_type: Component type (R, C, L, etc.)
            name: Component name
            value: Component value
            nodes: Connected nodes

        Returns:
            Validation result
        """
        result = ValidationResult()

        # Check component naming
        if not name.upper().startswith(component_type.upper()):
            result.add_error(
                name,
                f"Component name must start with '{component_type}'",
                suggestion=f"Rename to '{component_type}{name}'",
            )

        # Check node count
        expected_nodes = self._get_expected_node_count(component_type)
        if expected_nodes and len(nodes) != expected_nodes:
            result.add_error(name, f"Expected {expected_nodes} nodes, got {len(nodes)}")

        # Check value format
        if not self._is_valid_value(component_type, value):
            result.add_error(
                name,
                f"Invalid value format: {value}",
                suggestion="Use standard SPICE notation (e.g., 1k, 10u, 2.2n)",
            )

        return result

    def add_model_library(self, model_names: Union[str, List[str]]) -> None:
        """Add known model names to the library.

        Args:
            model_names: Model name(s) to add
        """
        if isinstance(model_names, str):
            model_names = [model_names]

        self._model_library.update(model_names)
        _logger.debug("Added %d models to library", len(model_names))

    def add_subcircuit(self, subcircuit_name: str) -> None:
        """Register a known subcircuit.

        Args:
            subcircuit_name: Subcircuit name
        """
        self._known_subcircuits.add(subcircuit_name)

    def add_custom_rule(self, rule_function: Callable[..., Any]) -> None:
        """Add a custom validation rule.

        Args:
            rule_function: Function that takes (components, directives, result)
        """
        self._custom_rules.append(rule_function)

    def _parse_netlist(
        self, netlist_content: str
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Set[str]]:
        """Parse netlist into components and directives.

        Returns:
            Tuple of (components, directives, nodes)
        """
        components: List[Dict[str, Any]] = []
        directives: List[Dict[str, Any]] = []
        nodes = set()

        lines = netlist_content.strip().split("\n")

        for line_num, line in enumerate(lines, 1):
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("*"):
                continue

            # Handle continuation lines
            if line.startswith("+"):
                if components:
                    components[-1]["line"] += " " + line[1:].strip()
                elif directives:
                    directives[-1]["line"] += " " + line[1:].strip()
                continue

            # Parse based on first character
            first_char = line[0].upper()

            if first_char == ".":
                # Directive
                parts = line.split()
                directives.append(
                    {
                        "type": parts[0].upper(),
                        "line": line,
                        "line_num": line_num,
                        "params": parts[1:] if len(parts) > 1 else [],
                    }
                )

            elif first_char in "RCLVIMQDJKEFGHSTXYZ":
                # Component
                parts = line.split()
                if len(parts) >= 2:
                    comp_nodes = self._extract_component_nodes(first_char, parts)
                    nodes.update(comp_nodes)

                    components.append(
                        {
                            "type": first_char,
                            "name": parts[0],
                            "nodes": comp_nodes,
                            "line": line,
                            "line_num": line_num,
                            "value": self._extract_component_value(first_char, parts),
                        }
                    )

        # Add ground node
        nodes.add("0")

        return components, directives, nodes

    def _extract_component_nodes(self, comp_type: str, parts: List[str]) -> List[str]:
        """Extract node names from component definition."""
        # Node count based on component type
        node_counts = {
            "R": 2,
            "C": 2,
            "L": 2,
            "V": 2,
            "I": 2,
            "D": 2,
            "Q": 3,
            "J": 3,
            "M": 4,
            "E": 4,
            "F": 2,
            "G": 4,
            "H": 2,
            "K": 0,  # K (coupling) handled specially
        }

        count = node_counts.get(comp_type, 0)
        if comp_type == "X":  # Subcircuit - variable nodes
            # Find where the subcircuit name is
            for i, part in enumerate(parts[1:], 1):
                if not part[0].isdigit() and part not in ["0", "GND"]:
                    count = i - 1
                    break

        return parts[1 : count + 1] if count > 0 else []

    def _extract_component_value(
        self, comp_type: str, parts: List[str]
    ) -> Optional[str]:
        """Extract component value from definition."""
        if comp_type in "RCL":
            # Simple passive components
            return parts[3] if len(parts) > 3 else None
        elif comp_type in "VI":
            # Sources - may have complex values
            return " ".join(parts[3:]) if len(parts) > 3 else None
        elif comp_type in "DQJM":
            # Semiconductor devices - model name
            node_count = {"D": 2, "Q": 3, "J": 3, "M": 4}[comp_type]
            return parts[node_count + 1] if len(parts) > node_count + 1 else None
        else:
            return None

    def _check_connectivity(
        self,
        components: List[Dict[str, Any]],
        nodes: Set[str],
        result: ValidationResult,
    ) -> None:
        """Check circuit connectivity."""
        # Count connections per node
        node_connections: Dict[str, int] = defaultdict(int)
        for comp in components:
            for node in comp["nodes"]:
                node_connections[node] += 1

        # Check for floating nodes
        for node, count in node_connections.items():
            if count == 1 and node != "0":
                result.add_warning(
                    None,
                    f"Node '{node}' has only one connection (floating)",
                    suggestion="Connect to ground or another component",
                )

        # Check for ground connection
        if "0" not in nodes and "GND" not in nodes:
            result.add_error(
                None,
                "No ground reference found in circuit",
                suggestion="Add a ground connection (node 0 or GND)",
            )

        # Check for orphaned components
        for comp in components:
            if comp["type"] != "K" and not comp["nodes"]:
                result.add_error(comp["name"], "Component has no node connections")

    def _check_component_values(
        self, components: List[Dict], result: ValidationResult
    ) -> None:
        """Check component values."""
        for comp in components:
            comp_type = comp["type"]
            value = comp["value"]

            if not value and comp_type in "RCL":
                result.add_error(comp["name"], "Missing component value")
                continue

            # Check passive component values
            if comp_type in "RCL" and value:
                if not re.match(core_patterns.FLOAT_NUMBER_PATTERN, value):
                    result.add_error(
                        comp["name"],
                        f"Invalid value format: {value}",
                        suggestion="Use SPICE notation (e.g., 1k, 10u)",
                    )
                else:
                    # Check for reasonable ranges
                    numeric_value = self._parse_spice_value(value)
                    if numeric_value is not None:
                        if comp_type == "R" and (
                            numeric_value < 1e-6 or numeric_value > 1e12
                        ):
                            result.add_warning(
                                comp["name"],
                                f"Unusual resistance value: {value}",
                                suggestion="Typical range: 1µΩ to 1TΩ",
                            )
                        elif comp_type == "C" and (
                            numeric_value < 1e-15 or numeric_value > 1
                        ):
                            result.add_warning(
                                comp["name"],
                                f"Unusual capacitance value: {value}",
                                suggestion="Typical range: 1fF to 1F",
                            )
                        elif comp_type == "L" and (
                            numeric_value < 1e-12 or numeric_value > 1000
                        ):
                            result.add_warning(
                                comp["name"],
                                f"Unusual inductance value: {value}",
                                suggestion="Typical range: 1pH to 1kH",
                            )

    def _check_models(self, components: List[Dict], result: ValidationResult) -> None:
        """Check model references."""
        for comp in components:
            if comp["type"] in "DQJM":
                model_name = comp["value"]
                if model_name and model_name not in self._model_library:
                    result.add_warning(
                        comp["name"],
                        f"Model '{model_name}' not found in library",
                        suggestion="Add .model statement or include model library",
                    )

            elif comp["type"] == "X":
                # Check subcircuit
                parts = comp["line"].split()
                if len(parts) > len(comp["nodes"]) + 1:
                    subckt_name = parts[len(comp["nodes"]) + 1]
                    if subckt_name not in self._known_subcircuits:
                        result.add_warning(
                            comp["name"],
                            f"Subcircuit '{subckt_name}' not found",
                            suggestion="Add .subckt definition or include library",
                        )

    def _check_directives(
        self, directives: List[Dict], result: ValidationResult
    ) -> None:
        """Check simulation directives."""
        # Track what analyses are defined
        analyses = set()

        for directive in directives:
            dir_type = directive["type"]

            if dir_type in [".TRAN", ".AC", ".DC", ".NOISE", ".TF"]:
                analyses.add(dir_type)

                # Check parameter count
                if dir_type == ".TRAN" and len(directive["params"]) < 1:
                    result.add_error(
                        None,
                        ".TRAN requires at least stop time",
                        location=f"Line {directive['line_num']}",
                    )
                elif dir_type == ".AC" and len(directive["params"]) < 3:
                    result.add_error(
                        None,
                        ".AC requires sweep type, points, and frequency range",
                        location=f"Line {directive['line_num']}",
                    )
                elif dir_type == ".DC" and len(directive["params"]) < 3:
                    result.add_error(
                        None,
                        ".DC requires source and sweep range",
                        location=f"Line {directive['line_num']}",
                    )

            elif dir_type == ".PARAM":
                # Check parameter syntax
                if not directive["params"]:
                    result.add_error(
                        None,
                        ".PARAM requires parameter definition",
                        location=f"Line {directive['line_num']}",
                    )

            elif dir_type == ".INCLUDE":
                # Check include file
                if directive["params"]:
                    include_file = directive["params"][0].strip("\"'")
                    if not Path(include_file).exists():
                        result.add_warning(
                            None,
                            f"Include file not found: {include_file}",
                            location=f"Line {directive['line_num']}",
                        )

        # Check for analysis directive
        if not analyses:
            result.add_info(
                None,
                "No analysis directive found (.tran, .ac, .dc, etc.). Add analysis directive to run simulation",
            )

    def _check_common_mistakes(
        self,
        components: List[Dict[str, Any]],
        directives: List[Dict[str, Any]],
        result: ValidationResult,
    ) -> None:
        """Check for common circuit mistakes."""
        # Check for voltage sources in parallel
        voltage_sources = [c for c in components if c["type"] == "V"]
        for i, v1 in enumerate(voltage_sources):
            for v2 in voltage_sources[i + 1 :]:
                if set(v1["nodes"]) == set(v2["nodes"]):
                    result.add_warning(
                        f"{v1['name']}, {v2['name']}",
                        "Voltage sources in parallel",
                        suggestion="Add series resistance or remove one source",
                    )

        # Check for current sources in series
        current_sources = [c for c in components if c["type"] == "I"]
        # This is more complex - would need full circuit analysis

        # Check for missing DC path to ground
        inductors = [c for c in components if c["type"] == "L"]
        if inductors and not any(c["type"] == "R" for c in components):
            result.add_warning(
                None,
                "Circuit has inductors but no resistors",
                suggestion="Add DC path to ground for initial conditions",
            )

        # Check for capacitor loops
        capacitors = [c for c in components if c["type"] == "C"]
        if len(capacitors) > 2:
            # Simple check - more than 2 capacitors might form a loop
            result.add_info(
                None,
                "Multiple capacitors detected - check for capacitor loops. Capacitor loops require initial conditions",
            )

    def _check_custom_rules(
        self,
        components: List[Dict[str, Any]],
        directives: List[Dict[str, Any]],
        result: ValidationResult,
    ) -> None:
        """Run custom validation rules."""
        for rule in self._custom_rules:
            try:
                rule(components, directives, result)
            except Exception as e:
                _logger.error("Error in custom rule: %s", e)

    def _get_expected_node_count(self, comp_type: str) -> Optional[int]:
        """Get expected node count for component type."""
        node_counts = {
            "R": 2,
            "C": 2,
            "L": 2,
            "V": 2,
            "I": 2,
            "D": 2,
            "Q": 3,
            "J": 3,
            "M": 4,
            "E": 4,
            "F": 2,
            "G": 4,
            "H": 2,
        }
        return node_counts.get(comp_type.upper())

    def _is_valid_value(self, comp_type: str, value: str) -> bool:
        """Check if component value is valid."""
        if comp_type.upper() in "RCL":
            return bool(re.match(core_patterns.FLOAT_NUMBER_PATTERN, value))
        return True  # Other components have complex value formats

    def _parse_spice_value(self, value: str) -> Optional[float]:
        """Parse SPICE value to float."""
        try:
            # Remove any trailing units
            value = re.sub(r"[a-zA-Z]+$", "", value)

            # Handle SPICE multipliers
            multipliers = {
                "T": 1e12,
                "G": 1e9,
                "MEG": 1e6,
                "K": 1e3,
                "M": 1e-3,
                "U": 1e-6,
                "N": 1e-9,
                "P": 1e-12,
                "F": 1e-15,
            }

            for suffix, mult in multipliers.items():
                if value.upper().endswith(suffix):
                    base = value[: -len(suffix)]
                    return float(base) * mult

            return float(value)
        except:
            return None
