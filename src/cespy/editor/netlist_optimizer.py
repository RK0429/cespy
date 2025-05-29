#!/usr/bin/env python
# coding=utf-8
"""Netlist optimizer for improving simulation performance.

This module provides optimization techniques for SPICE netlists to improve
simulation speed and convergence, including:
- Node ordering optimization
- Parasitic element removal
- Model simplification
- Subcircuit flattening
"""

import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from ..core import constants as core_constants
from ..core import patterns as core_patterns
from ..exceptions import OptimizationError

_logger = logging.getLogger("cespy.NetlistOptimizer")


class OptimizationLevel(Enum):
    """Optimization aggressiveness levels."""

    CONSERVATIVE = "conservative"  # Safe optimizations only
    MODERATE = "moderate"  # Balance between safety and performance
    AGGRESSIVE = "aggressive"  # Maximum performance, may affect accuracy


@dataclass
class OptimizationConfig:
    """Configuration for netlist optimization."""

    level: OptimizationLevel = OptimizationLevel.MODERATE
    remove_small_parasitics: bool = True
    parasitic_threshold: float = 1e-15  # Remove caps < 1fF, inductors < 1pH
    simplify_models: bool = True
    flatten_subcircuits: bool = False
    optimize_node_order: bool = True
    merge_series_resistors: bool = True
    merge_parallel_capacitors: bool = True
    remove_dangling_components: bool = True
    compress_node_names: bool = False
    remove_comments: bool = False

    def for_level(self, level: OptimizationLevel) -> "OptimizationConfig":
        """Get configuration for a specific optimization level."""
        config = OptimizationConfig(level=level)

        if level == OptimizationLevel.CONSERVATIVE:
            config.remove_small_parasitics = True
            config.parasitic_threshold = 1e-18  # Only remove extremely small values
            config.simplify_models = False
            config.flatten_subcircuits = False
            config.merge_series_resistors = True
            config.merge_parallel_capacitors = True
            config.remove_dangling_components = True
            config.compress_node_names = False
            config.remove_comments = False

        elif level == OptimizationLevel.MODERATE:
            # Default values as initialized
            pass

        elif level == OptimizationLevel.AGGRESSIVE:
            config.remove_small_parasitics = True
            config.parasitic_threshold = 1e-12  # Remove caps < 1pF, inductors < 1nH
            config.simplify_models = True
            config.flatten_subcircuits = True
            config.merge_series_resistors = True
            config.merge_parallel_capacitors = True
            config.remove_dangling_components = True
            config.compress_node_names = True
            config.remove_comments = True

        return config


@dataclass
class OptimizationResult:
    """Results of netlist optimization."""

    original_line_count: int = 0
    optimized_line_count: int = 0
    components_removed: int = 0
    components_merged: int = 0
    nodes_renamed: int = 0
    subcircuits_flattened: int = 0
    models_simplified: int = 0
    warnings: List[str] = field(default_factory=list)

    @property
    def reduction_percentage(self) -> float:
        """Calculate line count reduction percentage."""
        if self.original_line_count == 0:
            return 0.0
        return (
            (self.original_line_count - self.optimized_line_count)
            / self.original_line_count
            * 100.0
        )


class NetlistOptimizer:
    """Optimizes SPICE netlists for better simulation performance.

    This class provides various optimization techniques to improve
    simulation speed without significantly affecting accuracy.
    """

    def __init__(self, config: Optional[OptimizationConfig] = None):
        """Initialize netlist optimizer.

        Args:
            config: Optimization configuration
        """
        self.config = config or OptimizationConfig()
        self._node_map: Dict[str, str] = {}
        self._component_map: Dict[str, List[str]] = defaultdict(list)
        self._subcircuit_defs: Dict[str, List[str]] = {}
        self._model_defs: Dict[str, str] = {}

        _logger.info(
            "NetlistOptimizer initialized with level: %s", self.config.level.value
        )

    def optimize_netlist(self, netlist_content: str) -> Tuple[str, OptimizationResult]:
        """Optimize a SPICE netlist.

        Args:
            netlist_content: Original netlist content

        Returns:
            Tuple of (optimized_netlist, optimization_result)
        """
        result = OptimizationResult()
        lines = netlist_content.strip().split("\n")
        result.original_line_count = len(lines)

        # Parse netlist structure
        self._parse_netlist(lines)

        # Apply optimizations based on configuration
        if self.config.remove_comments:
            lines = self._remove_comments(lines)

        if self.config.remove_dangling_components:
            lines, removed = self._remove_dangling_components(lines)
            result.components_removed += removed

        if self.config.remove_small_parasitics:
            lines, removed = self._remove_small_parasitics(lines)
            result.components_removed += removed

        if self.config.merge_series_resistors or self.config.merge_parallel_capacitors:
            lines, merged = self._merge_components(lines)
            result.components_merged += merged

        if self.config.simplify_models:
            lines, simplified = self._simplify_models(lines)
            result.models_simplified += simplified

        if self.config.flatten_subcircuits:
            lines, flattened = self._flatten_subcircuits(lines)
            result.subcircuits_flattened += flattened

        if self.config.optimize_node_order:
            lines = self._optimize_node_order(lines)

        if self.config.compress_node_names:
            lines, renamed = self._compress_node_names(lines)
            result.nodes_renamed += renamed

        # Clean up empty lines
        lines = [line for line in lines if line.strip()]

        result.optimized_line_count = len(lines)
        optimized_netlist = "\n".join(lines)

        _logger.info(
            "Optimization complete: %d%% reduction", result.reduction_percentage
        )

        return optimized_netlist, result

    def optimize_file(self, input_file: Path, output_file: Path) -> OptimizationResult:
        """Optimize a netlist file.

        Args:
            input_file: Input netlist file
            output_file: Output file for optimized netlist

        Returns:
            OptimizationResult
        """
        with open(input_file, "r", encoding="utf-8") as f:
            content = f.read()

        optimized_content, result = self.optimize_netlist(content)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(optimized_content)

        _logger.info("Optimized %s -> %s", input_file, output_file)

        return result

    def _parse_netlist(self, lines: List[str]) -> None:
        """Parse netlist structure for optimization."""
        self._node_map.clear()
        self._component_map.clear()
        self._subcircuit_defs.clear()
        self._model_defs.clear()

        in_subckt = False
        current_subckt = None

        for line in lines:
            line = line.strip()
            if not line or line.startswith("*"):
                continue

            # Track subcircuit definitions
            if line.upper().startswith(".SUBCKT"):
                parts = line.split()
                if len(parts) > 1:
                    current_subckt = parts[1]
                    in_subckt = True
                    self._subcircuit_defs[current_subckt] = []
            elif line.upper().startswith(".ENDS"):
                in_subckt = False
                current_subckt = None
            elif in_subckt and current_subckt:
                self._subcircuit_defs[current_subckt].append(line)

            # Track model definitions
            if line.upper().startswith(".MODEL"):
                parts = line.split()
                if len(parts) > 1:
                    self._model_defs[parts[1]] = line

            # Track components by type
            if line and line[0].isalpha() and not line.startswith("."):
                comp_type = line[0].upper()
                self._component_map[comp_type].append(line)

    def _remove_comments(self, lines: List[str]) -> List[str]:
        """Remove comment lines."""
        return [line for line in lines if not line.strip().startswith("*")]

    def _remove_small_parasitics(self, lines: List[str]) -> Tuple[List[str], int]:
        """Remove small parasitic components."""
        from ..editor.base_editor import scan_eng

        filtered_lines = []
        removed_count = 0

        for line in lines:
            should_remove = False

            if line.strip() and line[0] in "CL":
                # Check capacitors and inductors
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        value = scan_eng(parts[3])
                        if abs(value) < self.config.parasitic_threshold:
                            should_remove = True
                            removed_count += 1
                            _logger.debug("Removing small parasitic: %s", line.strip())
                    except ValueError:
                        pass

            if not should_remove:
                filtered_lines.append(line)

        return filtered_lines, removed_count

    def _remove_dangling_components(self, lines: List[str]) -> Tuple[List[str], int]:
        """Remove components with unconnected nodes."""
        # First, collect all nodes
        all_nodes = set(["0", "GND"])  # Ground nodes
        node_connections = defaultdict(int)

        # Count node connections
        for line in lines:
            if line.strip() and line[0].isalpha() and not line.startswith("."):
                parts = line.split()
                comp_type = line[0].upper()

                # Extract nodes based on component type
                if comp_type in "RCL":
                    if len(parts) >= 3:
                        node_connections[parts[1]] += 1
                        node_connections[parts[2]] += 1
                elif comp_type in "VI":
                    if len(parts) >= 3:
                        node_connections[parts[1]] += 1
                        node_connections[parts[2]] += 1
                elif comp_type == "D":
                    if len(parts) >= 3:
                        node_connections[parts[1]] += 1
                        node_connections[parts[2]] += 1
                # Add more component types as needed

        # Find dangling nodes (connected to only one component)
        dangling_nodes = {
            node
            for node, count in node_connections.items()
            if count == 1 and node not in ["0", "GND"]
        }

        # Remove components connected to dangling nodes
        filtered_lines = []
        removed_count = 0

        for line in lines:
            should_remove = False

            if line.strip() and line[0].isalpha() and not line.startswith("."):
                parts = line.split()
                if len(parts) >= 3:
                    # Check if any node is dangling
                    for i in range(1, min(4, len(parts))):
                        if parts[i] in dangling_nodes:
                            should_remove = True
                            removed_count += 1
                            _logger.debug(
                                "Removing dangling component: %s", line.strip()
                            )
                            break

            if not should_remove:
                filtered_lines.append(line)

        return filtered_lines, removed_count

    def _merge_components(self, lines: List[str]) -> Tuple[List[str], int]:
        """Merge series resistors and parallel capacitors."""
        from ..editor.base_editor import scan_eng, format_eng

        merged_count = 0

        # This is a simplified implementation
        # A full implementation would need circuit topology analysis

        # Group components by nodes
        resistors_by_nodes = defaultdict(list)
        capacitors_by_nodes = defaultdict(list)

        component_lines = {}

        for i, line in enumerate(lines):
            if line.strip() and line[0] in "RC":
                parts = line.split()
                if len(parts) >= 4:
                    comp_ref = parts[0]
                    node1, node2 = parts[1], parts[2]
                    nodes = tuple(sorted([node1, node2]))

                    component_lines[comp_ref] = i

                    if line[0] == "R" and self.config.merge_series_resistors:
                        resistors_by_nodes[nodes].append((comp_ref, parts[3]))
                    elif line[0] == "C" and self.config.merge_parallel_capacitors:
                        capacitors_by_nodes[nodes].append((comp_ref, parts[3]))

        lines_to_remove = set()
        lines_to_modify = {}

        # Merge parallel capacitors
        for nodes, caps in capacitors_by_nodes.items():
            if len(caps) > 1:
                # Sum capacitance values
                total_cap = 0
                refs_to_merge = []

                try:
                    for ref, value_str in caps:
                        total_cap += scan_eng(value_str)
                        refs_to_merge.append(ref)

                    # Keep first capacitor, remove others
                    first_ref = refs_to_merge[0]
                    first_line_idx = component_lines[first_ref]

                    # Update first capacitor with total value
                    parts = lines[first_line_idx].split()
                    parts[3] = format_eng(total_cap)
                    lines_to_modify[first_line_idx] = " ".join(parts)

                    # Mark others for removal
                    for ref in refs_to_merge[1:]:
                        lines_to_remove.add(component_lines[ref])
                        merged_count += 1

                except ValueError:
                    _logger.warning("Could not merge capacitors: %s", caps)

        # Apply modifications
        result_lines = []
        for i, line in enumerate(lines):
            if i in lines_to_remove:
                continue
            elif i in lines_to_modify:
                result_lines.append(lines_to_modify[i])
            else:
                result_lines.append(line)

        return result_lines, merged_count

    def _simplify_models(self, lines: List[str]) -> Tuple[List[str], int]:
        """Simplify device models by removing less significant parameters."""
        simplified_count = 0

        # Parameters to keep for different model types (simplified list)
        essential_params = {
            "D": ["IS", "RS", "N", "CJO", "VJ", "M", "BV"],  # Diode
            "NPN": ["IS", "BF", "VAF", "CJE", "CJC", "TF", "TR"],  # BJT
            "PNP": ["IS", "BF", "VAF", "CJE", "CJC", "TF", "TR"],  # BJT
            "NMOS": ["VTO", "KP", "LAMBDA", "CGS", "CGD", "CJ"],  # MOSFET
            "PMOS": ["VTO", "KP", "LAMBDA", "CGS", "CGD", "CJ"],  # MOSFET
        }

        result_lines = []

        for line in lines:
            if line.upper().strip().startswith(".MODEL"):
                parts = line.split()
                if len(parts) >= 3:
                    model_name = parts[1]
                    model_type = parts[2].upper()

                    if (
                        model_type in essential_params
                        and self.config.level == OptimizationLevel.AGGRESSIVE
                    ):
                        # Parse parameters
                        param_str = " ".join(parts[3:])
                        param_pairs = re.findall(r"(\w+)\s*=\s*([^\s()]+)", param_str)

                        # Keep only essential parameters
                        essential = essential_params[model_type]
                        filtered_params = [
                            (p, v) for p, v in param_pairs if p.upper() in essential
                        ]

                        if len(filtered_params) < len(param_pairs):
                            simplified_count += 1
                            # Rebuild model line
                            new_line = f".MODEL {model_name} {model_type}"
                            if filtered_params:
                                new_line += " " + " ".join(
                                    [f"{p}={v}" for p, v in filtered_params]
                                )
                            result_lines.append(new_line)
                            continue

            result_lines.append(line)

        return result_lines, simplified_count

    def _flatten_subcircuits(self, lines: List[str]) -> Tuple[List[str], int]:
        """Flatten simple subcircuits inline."""
        # This is a complex operation that would require full netlist parsing
        # For now, we'll just return the original lines
        _logger.warning("Subcircuit flattening not yet implemented")
        return lines, 0

    def _optimize_node_order(self, lines: List[str]) -> List[str]:
        """Optimize node ordering for better matrix structure."""
        # This would require sophisticated graph analysis
        # For now, we'll just ensure ground node is first

        result_lines = []

        for line in lines:
            if line.strip() and line[0].isalpha() and not line.startswith("."):
                parts = line.split()
                comp_type = line[0].upper()

                # For 2-terminal devices, put ground node first if present
                if comp_type in "RCLVI" and len(parts) >= 3:
                    node1, node2 = parts[1], parts[2]
                    if node2 in ["0", "GND"] and node1 not in ["0", "GND"]:
                        # Swap nodes
                        parts[1], parts[2] = parts[2], parts[1]
                        line = " ".join(parts)

            result_lines.append(line)

        return result_lines

    def _compress_node_names(self, lines: List[str]) -> Tuple[List[str], int]:
        """Compress node names to shorter versions."""
        # Build node mapping
        node_map = {"0": "0", "GND": "0"}  # Keep ground as-is
        node_counter = 1
        renamed_count = 0

        # First pass: collect all unique nodes
        all_nodes = set()
        for line in lines:
            if line.strip() and line[0].isalpha() and not line.startswith("."):
                parts = line.split()
                # Extract nodes (simplified - assumes standard component formats)
                for i in range(1, min(5, len(parts))):
                    if not parts[i].startswith("+") and not parts[i].startswith("-"):
                        all_nodes.add(parts[i])

        # Create mapping for non-ground nodes
        for node in sorted(all_nodes):
            if node not in ["0", "GND"]:
                node_map[node] = f"n{node_counter}"
                node_counter += 1
                renamed_count += 1

        # Second pass: apply mapping
        result_lines = []
        for line in lines:
            if line.strip() and line[0].isalpha() and not line.startswith("."):
                parts = line.split()
                # Replace nodes
                for i in range(1, min(5, len(parts))):
                    if parts[i] in node_map:
                        parts[i] = node_map[parts[i]]
                line = " ".join(parts)

            result_lines.append(line)

        return result_lines, renamed_count

    def analyze_optimization_impact(
        self, original: str, optimized: str
    ) -> Dict[str, Any]:
        """Analyze the impact of optimization on the netlist.

        Args:
            original: Original netlist content
            optimized: Optimized netlist content

        Returns:
            Dictionary with impact analysis
        """
        analysis = {
            "size_reduction": len(original) - len(optimized),
            "size_reduction_pct": (1 - len(optimized) / len(original)) * 100
            if len(original) > 0
            else 0,
            "line_reduction": original.count("\n") - optimized.count("\n"),
            "component_types_affected": set(),
            "warnings": [],
        }

        # Count components by type
        orig_components = defaultdict(int)
        opt_components = defaultdict(int)

        for line in original.split("\n"):
            if line.strip() and line[0].isalpha() and not line.startswith("."):
                orig_components[line[0].upper()] += 1

        for line in optimized.split("\n"):
            if line.strip() and line[0].isalpha() and not line.startswith("."):
                opt_components[line[0].upper()] += 1

        # Find affected component types
        for comp_type in orig_components:
            if orig_components[comp_type] != opt_components.get(comp_type, 0):
                analysis["component_types_affected"].add(comp_type)

        # Add warnings for significant changes
        if analysis["size_reduction_pct"] > 50:
            analysis["warnings"].append(
                "Large size reduction - verify simulation accuracy"
            )

        if "X" in analysis["component_types_affected"]:
            analysis["warnings"].append(
                "Subcircuits were modified - check hierarchical behavior"
            )

        return analysis
