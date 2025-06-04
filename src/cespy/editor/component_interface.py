#!/usr/bin/env python
# coding=utf-8
# pylint: disable=unnecessary-ellipsis
"""Component interface protocol for editor components.

This module defines the standard interface that all circuit components
must implement, ensuring consistent behavior across different editor types.
"""

from abc import abstractmethod
from typing import Any, Dict, List, Protocol, Union


class ComponentInterface(Protocol):
    """Protocol defining the standard interface for circuit components.

    All component implementations must provide these methods to ensure
    consistent manipulation across different schematic formats.
    """

    @abstractmethod
    def get_name(self) -> str:
        """Get the component name/identifier.

        Returns:
            Component name (e.g., 'R1', 'C2', 'U1')
        """
        ...

    @abstractmethod
    def get_type(self) -> str:
        """Get the component type.

        Returns:
            Component type (e.g., 'resistor', 'capacitor', 'voltage_source')
        """
        ...

    @abstractmethod
    def set_value(self, value: Union[str, float]) -> None:
        """Set the component's primary value.

        Args:
            value: New value for the component

        Raises:
            ValueError: If value is invalid for this component type
        """
        ...

    @abstractmethod
    def get_value(self) -> Union[str, float, None]:
        """Get the component's primary value.

        Returns:
            Component value or None if not set
        """
        ...

    @abstractmethod
    def get_attributes(self) -> Dict[str, Any]:
        """Get all component attributes.

        Returns:
            Dictionary of attribute names to values
        """
        ...

    @abstractmethod
    def set_attribute(self, name: str, value: Any) -> None:
        """Set a specific attribute.

        Args:
            name: Attribute name
            value: Attribute value

        Raises:
            KeyError: If attribute name is not valid for this component
        """
        ...

    @abstractmethod
    def get_attribute(self, name: str) -> Any:
        """Get a specific attribute value.

        Args:
            name: Attribute name

        Returns:
            Attribute value

        Raises:
            KeyError: If attribute does not exist
        """
        ...

    @abstractmethod
    def validate(self) -> List[str]:
        """Validate the component configuration.

        Returns:
            List of validation error messages (empty if valid)
        """
        ...

    @abstractmethod
    def get_pins(self) -> List[str]:
        """Get list of component pins/terminals.

        Returns:
            List of pin names or numbers
        """
        ...

    @abstractmethod
    def get_connected_nets(self) -> Dict[str, str]:
        """Get nets connected to each pin.

        Returns:
            Dictionary mapping pin names to net names
        """
        ...

    @abstractmethod
    def connect_pin(self, pin: str, net: str) -> None:
        """Connect a pin to a net.

        Args:
            pin: Pin name/number
            net: Net name to connect to

        Raises:
            ValueError: If pin name is invalid
        """
        ...

    @abstractmethod
    def get_position(self) -> tuple[float, float]:
        """Get component position.

        Returns:
            Tuple of (x, y) coordinates
        """
        ...

    @abstractmethod
    def set_position(self, x: float, y: float) -> None:
        """Set component position.

        Args:
            x: X coordinate
            y: Y coordinate
        """
        ...

    @abstractmethod
    def get_rotation(self) -> float:
        """Get component rotation angle.

        Returns:
            Rotation angle in degrees
        """
        ...

    @abstractmethod
    def set_rotation(self, angle: float) -> None:
        """Set component rotation angle.

        Args:
            angle: Rotation angle in degrees
        """
        ...

    @abstractmethod
    def is_flipped(self) -> bool:
        """Check if component is flipped/mirrored.

        Returns:
            True if flipped, False otherwise
        """
        ...

    @abstractmethod
    def set_flipped(self, flipped: bool) -> None:
        """Set component flip state.

        Args:
            flipped: True to flip, False for normal
        """
        ...

    @abstractmethod
    def clone(self) -> "ComponentInterface":
        """Create a copy of this component.

        Returns:
            New component instance with same attributes
        """
        ...

    @abstractmethod
    def to_spice(self) -> str:
        """Convert component to SPICE netlist format.

        Returns:
            SPICE netlist line(s) for this component
        """
        ...
