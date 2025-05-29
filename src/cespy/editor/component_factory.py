#!/usr/bin/env python
# coding=utf-8
"""Component factory for creating circuit component objects.

This module provides a factory pattern implementation for creating
component objects based on type and attributes, supporting multiple
schematic formats.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

from ..core import constants as core_constants
from ..core import patterns as core_patterns
from ..exceptions import ComponentNotFoundError, InvalidComponentError

_logger = logging.getLogger("cespy.ComponentFactory")


class ComponentType(Enum):
    """Standard component types."""
    # Passive components
    RESISTOR = "resistor"
    CAPACITOR = "capacitor"
    INDUCTOR = "inductor"
    
    # Sources
    VOLTAGE_SOURCE = "voltage_source"
    CURRENT_SOURCE = "current_source"
    VOLTAGE_CONTROLLED_VOLTAGE_SOURCE = "vcvs"
    VOLTAGE_CONTROLLED_CURRENT_SOURCE = "vccs"
    CURRENT_CONTROLLED_VOLTAGE_SOURCE = "ccvs"
    CURRENT_CONTROLLED_CURRENT_SOURCE = "cccs"
    
    # Semiconductors
    DIODE = "diode"
    BJT = "bjt"
    MOSFET = "mosfet"
    JFET = "jfet"
    
    # Other
    SUBCIRCUIT = "subcircuit"
    GROUND = "ground"
    NODE = "node"
    TEXT = "text"
    WIRE = "wire"


@dataclass
class ComponentTemplate:
    """Template for creating components."""
    component_type: ComponentType
    prefix: str
    default_value: Optional[str] = None
    required_attributes: List[str] = field(default_factory=list)
    optional_attributes: List[str] = field(default_factory=list)
    pin_names: List[str] = field(default_factory=list)
    spice_template: str = ""
    validation_pattern: Optional[str] = None


class BaseComponent:
    """Base implementation of ComponentInterface."""
    
    def __init__(self, name: str, component_type: ComponentType):
        """Initialize base component.
        
        Args:
            name: Component name/identifier
            component_type: Type of component
        """
        self.name = name
        self.component_type = component_type
        self.attributes: Dict[str, Any] = {}
        self.position = (0.0, 0.0)
        self.rotation = 0.0
        self.flipped = False
        self.pin_connections: Dict[str, str] = {}
        
    def get_name(self) -> str:
        """Get component name."""
        return self.name
    
    def get_type(self) -> str:
        """Get component type."""
        return self.component_type.value
    
    def set_value(self, value: Union[str, float]) -> None:
        """Set component value."""
        self.attributes["value"] = str(value)
    
    def get_value(self) -> Union[str, float, None]:
        """Get component value."""
        return self.attributes.get("value")
    
    def get_attributes(self) -> Dict[str, Any]:
        """Get all attributes."""
        return self.attributes.copy()
    
    def set_attribute(self, name: str, value: Any) -> None:
        """Set attribute value."""
        self.attributes[name] = value
    
    def get_attribute(self, name: str) -> Any:
        """Get attribute value."""
        if name not in self.attributes:
            raise KeyError(f"Attribute '{name}' not found")
        return self.attributes[name]
    
    def validate(self) -> List[str]:
        """Validate component."""
        errors = []
        
        # Check name format
        if not self.name:
            errors.append("Component name is empty")
        
        # Component-specific validation
        template = COMPONENT_TEMPLATES.get(self.component_type)
        if template:
            # Check required attributes
            for attr in template.required_attributes:
                if attr not in self.attributes:
                    errors.append(f"Required attribute '{attr}' is missing")
            
            # Validate value format if pattern provided
            if template.validation_pattern and "value" in self.attributes:
                import re
                if not re.match(template.validation_pattern, str(self.attributes["value"])):
                    errors.append(f"Invalid value format: {self.attributes['value']}")
        
        return errors
    
    def get_pins(self) -> List[str]:
        """Get component pins."""
        template = COMPONENT_TEMPLATES.get(self.component_type)
        if template:
            return template.pin_names.copy()
        return []
    
    def get_connected_nets(self) -> Dict[str, str]:
        """Get connected nets."""
        return self.pin_connections.copy()
    
    def connect_pin(self, pin: str, net: str) -> None:
        """Connect pin to net."""
        pins = self.get_pins()
        if pin not in pins:
            raise ValueError(f"Invalid pin '{pin}' for component type {self.component_type.value}")
        self.pin_connections[pin] = net
    
    def get_position(self) -> tuple[float, float]:
        """Get position."""
        return self.position
    
    def set_position(self, x: float, y: float) -> None:
        """Set position."""
        self.position = (x, y)
    
    def get_rotation(self) -> float:
        """Get rotation."""
        return self.rotation
    
    def set_rotation(self, angle: float) -> None:
        """Set rotation."""
        self.rotation = angle % 360
    
    def is_flipped(self) -> bool:
        """Check if flipped."""
        return self.flipped
    
    def set_flipped(self, flipped: bool) -> None:
        """Set flipped state."""
        self.flipped = flipped
    
    def clone(self) -> 'BaseComponent':
        """Create a copy."""
        new_component = BaseComponent(self.name, self.component_type)
        new_component.attributes = self.attributes.copy()
        new_component.position = self.position
        new_component.rotation = self.rotation
        new_component.flipped = self.flipped
        new_component.pin_connections = self.pin_connections.copy()
        return new_component
    
    def to_spice(self) -> str:
        """Convert to SPICE format."""
        template = COMPONENT_TEMPLATES.get(self.component_type)
        if not template:
            return f"* Unknown component type: {self.component_type.value}"
        
        # Build SPICE line from template
        spice_line = template.spice_template
        
        # Replace placeholders
        spice_line = spice_line.replace("{name}", self.name)
        
        # Replace pin connections
        pins = self.get_pins()
        for i, pin in enumerate(pins):
            net = self.pin_connections.get(pin, f"NC_{pin}")
            spice_line = spice_line.replace(f"{{pin{i+1}}}", net)
        
        # Replace attributes
        for attr, value in self.attributes.items():
            spice_line = spice_line.replace(f"{{{attr}}}", str(value))
        
        return spice_line


# Define component templates
COMPONENT_TEMPLATES = {
    ComponentType.RESISTOR: ComponentTemplate(
        component_type=ComponentType.RESISTOR,
        prefix="R",
        default_value="1k",
        required_attributes=["value"],
        optional_attributes=["tolerance", "power", "tc1", "tc2"],
        pin_names=["1", "2"],
        spice_template="{name} {pin1} {pin2} {value}",
        validation_pattern=core_patterns.FLOAT_NUMBER_PATTERN
    ),
    
    ComponentType.CAPACITOR: ComponentTemplate(
        component_type=ComponentType.CAPACITOR,
        prefix="C",
        default_value="1n",
        required_attributes=["value"],
        optional_attributes=["tolerance", "voltage", "ic"],
        pin_names=["1", "2"],
        spice_template="{name} {pin1} {pin2} {value}",
        validation_pattern=core_patterns.FLOAT_NUMBER_PATTERN
    ),
    
    ComponentType.INDUCTOR: ComponentTemplate(
        component_type=ComponentType.INDUCTOR,
        prefix="L",
        default_value="1u",
        required_attributes=["value"],
        optional_attributes=["tolerance", "ic"],
        pin_names=["1", "2"],
        spice_template="{name} {pin1} {pin2} {value}",
        validation_pattern=core_patterns.FLOAT_NUMBER_PATTERN
    ),
    
    ComponentType.VOLTAGE_SOURCE: ComponentTemplate(
        component_type=ComponentType.VOLTAGE_SOURCE,
        prefix="V",
        default_value="0",
        required_attributes=["value"],
        optional_attributes=["ac", "dc", "pulse", "sin", "exp", "pwl", "sffm"],
        pin_names=["+", "-"],
        spice_template="{name} {pin1} {pin2} {value}",
        validation_pattern=None  # Complex value format
    ),
    
    ComponentType.CURRENT_SOURCE: ComponentTemplate(
        component_type=ComponentType.CURRENT_SOURCE,
        prefix="I",
        default_value="0",
        required_attributes=["value"],
        optional_attributes=["ac", "dc", "pulse", "sin", "exp", "pwl", "sffm"],
        pin_names=["+", "-"],
        spice_template="{name} {pin1} {pin2} {value}",
        validation_pattern=None  # Complex value format
    ),
    
    ComponentType.DIODE: ComponentTemplate(
        component_type=ComponentType.DIODE,
        prefix="D",
        default_value="1N4148",
        required_attributes=["model"],
        optional_attributes=["area", "ic", "temp"],
        pin_names=["anode", "cathode"],
        spice_template="{name} {pin1} {pin2} {model}",
        validation_pattern=None
    ),
    
    ComponentType.BJT: ComponentTemplate(
        component_type=ComponentType.BJT,
        prefix="Q",
        default_value="2N2222",
        required_attributes=["model"],
        optional_attributes=["area", "ic", "temp"],
        pin_names=["collector", "base", "emitter"],
        spice_template="{name} {pin1} {pin2} {pin3} {model}",
        validation_pattern=None
    ),
    
    ComponentType.MOSFET: ComponentTemplate(
        component_type=ComponentType.MOSFET,
        prefix="M",
        default_value="IRF540",
        required_attributes=["model"],
        optional_attributes=["w", "l", "ad", "as", "pd", "ps", "nrd", "nrs"],
        pin_names=["drain", "gate", "source", "bulk"],
        spice_template="{name} {pin1} {pin2} {pin3} {pin4} {model}",
        validation_pattern=None
    ),
    
    ComponentType.SUBCIRCUIT: ComponentTemplate(
        component_type=ComponentType.SUBCIRCUIT,
        prefix="X",
        default_value="",
        required_attributes=["subckt"],
        optional_attributes=["params"],
        pin_names=[],  # Dynamic based on subcircuit
        spice_template="{name} {pins} {subckt} {params}",
        validation_pattern=None
    ),
    
    ComponentType.GROUND: ComponentTemplate(
        component_type=ComponentType.GROUND,
        prefix="",
        default_value="0",
        required_attributes=[],
        optional_attributes=[],
        pin_names=["gnd"],
        spice_template="",  # Not included in SPICE
        validation_pattern=None
    ),
}


class ComponentFactory:
    """Factory for creating circuit components.
    
    This class provides methods to create component objects based on
    type and attributes, with support for different schematic formats
    and validation.
    """
    
    def __init__(self):
        """Initialize component factory."""
        self._custom_templates: Dict[str, ComponentTemplate] = {}
        self._component_classes: Dict[ComponentType, Type[BaseComponent]] = {}
        
        _logger.info("ComponentFactory initialized")
    
    def create_component(
        self,
        component_type: Union[ComponentType, str],
        name: Optional[str] = None,
        **attributes: Any
    ) -> BaseComponent:
        """Create a component instance.
        
        Args:
            component_type: Type of component to create
            name: Component name (auto-generated if None)
            **attributes: Component attributes
            
        Returns:
            Component instance
            
        Raises:
            InvalidComponentError: If component type is invalid
        """
        # Convert string to enum if needed
        if isinstance(component_type, str):
            try:
                component_type = ComponentType(component_type)
            except ValueError:
                raise InvalidComponentError(f"Unknown component type: {component_type}")
        
        # Get template
        template = COMPONENT_TEMPLATES.get(component_type)
        if not template:
            raise InvalidComponentError(f"No template for component type: {component_type}")
        
        # Generate name if not provided
        if not name:
            name = self._generate_component_name(component_type)
        
        # Get component class
        component_class = self._component_classes.get(component_type, BaseComponent)
        
        # Create component
        component = component_class(name, component_type)
        
        # Set default value
        if template.default_value:
            component.set_value(template.default_value)
        
        # Set provided attributes
        for attr_name, attr_value in attributes.items():
            component.set_attribute(attr_name, attr_value)
        
        _logger.debug("Created component %s of type %s", name, component_type.value)
        
        return component
    
    def create_from_spice_line(self, spice_line: str) -> Optional[BaseComponent]:
        """Create component from SPICE netlist line.
        
        Args:
            spice_line: SPICE netlist line
            
        Returns:
            Component instance or None if not a component line
        """
        import re
        
        # Skip comments and empty lines
        line = spice_line.strip()
        if not line or line.startswith("*"):
            return None
        
        # Determine component type from prefix
        prefix = line[0].upper()
        component_type = None
        
        for comp_type, template in COMPONENT_TEMPLATES.items():
            if template.prefix == prefix:
                component_type = comp_type
                break
        
        if not component_type:
            return None
        
        # Parse line based on component type
        parts = line.split()
        if len(parts) < 2:
            return None
        
        name = parts[0]
        template = COMPONENT_TEMPLATES[component_type]
        
        # Create component
        component = self.create_component(component_type, name)
        
        # Parse pin connections
        pin_count = len(template.pin_names)
        if len(parts) > pin_count:
            for i, pin_name in enumerate(template.pin_names):
                if i + 1 < len(parts):
                    component.connect_pin(pin_name, parts[i + 1])
        
        # Parse value and other attributes
        if component_type in [ComponentType.RESISTOR, ComponentType.CAPACITOR, ComponentType.INDUCTOR]:
            if len(parts) > pin_count + 1:
                component.set_value(parts[pin_count + 1])
        
        # TODO: Parse additional attributes based on component type
        
        return component
    
    def register_custom_template(self, name: str, template: ComponentTemplate) -> None:
        """Register a custom component template.
        
        Args:
            name: Template name
            template: Component template
        """
        self._custom_templates[name] = template
        _logger.info("Registered custom template: %s", name)
    
    def register_component_class(
        self,
        component_type: ComponentType,
        component_class: Type[BaseComponent]
    ) -> None:
        """Register a custom component class.
        
        Args:
            component_type: Component type
            component_class: Component class
        """
        self._component_classes[component_type] = component_class
        _logger.info("Registered custom class for %s", component_type.value)
    
    def get_component_types(self) -> List[ComponentType]:
        """Get list of available component types.
        
        Returns:
            List of component types
        """
        return list(ComponentType)
    
    def get_template(self, component_type: ComponentType) -> Optional[ComponentTemplate]:
        """Get template for a component type.
        
        Args:
            component_type: Component type
            
        Returns:
            Component template or None
        """
        return COMPONENT_TEMPLATES.get(component_type)
    
    def _generate_component_name(self, component_type: ComponentType) -> str:
        """Generate unique component name.
        
        Args:
            component_type: Component type
            
        Returns:
            Generated name
        """
        template = COMPONENT_TEMPLATES.get(component_type)
        if not template:
            return f"U_{id(self)}"
        
        # Simple counter-based generation
        # In production, this should track used names
        import time
        counter = int(time.time() * 1000) % 10000
        return f"{template.prefix}{counter}"