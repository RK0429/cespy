#!/usr/bin/env python
# coding=utf-8

# -------------------------------------------------------------------------------
#
#  ███████╗██████╗ ██╗ ██████╗███████╗██╗     ██╗██████╗
#  ██╔════╝██╔══██╗██║██╔════╝██╔════╝██║     ██║██╔══██╗
#  ███████╗██████╔╝██║██║     █████╗  ██║     ██║██████╔╝
#  ╚════██║██╔═══╝ ██║██║     ██╔══╝  ██║     ██║██╔══██╗
#  ███████║██║     ██║╚██████╗███████╗███████╗██║██████╔╝
#  ╚══════╝╚═╝     ╚═╝ ╚═════╝╚══════╝╚══════╝╚═╝╚═════╝
#
# Name:        failure_modes.py
# Purpose:     Class to automate FMEA
#
# Author:      Nuno Brum (nuno.brum@gmail.com)
#
# Created:     10-08-2023
# Licence:     refer to the LICENSE file
# -------------------------------------------------------------------------------

from collections import OrderedDict
from typing import Any, Dict, Iterable, Optional, Type, Union

from ...editor.base_editor import BaseEditor, ComponentNotFoundError
from ..sim_runner import AnyRunner, RunTask
from ..simulator import Simulator
from .sim_analysis import SimAnalysis


class FailureMode(SimAnalysis):
    """This Class will replace each component on the circuit for their failure modes and
    launch a simulation.

    The following failure modes are built-in:

    * Resistors, Capacitors, Inductors and Diodes
        # Open Circuit
        # Short Circuit

    * Transistors
        # Open Circuit (All pins)
        # Short Circuit (All pins)
        # Short Circuit Base-Emitter (Bipolar) / Gate-Source (MOS)
        # Short Circuit Collector-Emitter (Bipolar) / Drain-Source (MOS)

    * Integrated Circuits
        # The failure modes are defined by the user by using the add_failure_mode() method
    """

    def __init__(
        self,
        circuit_file: Union[str, BaseEditor],
        simulator: Optional[Type[Simulator]] = None,
        runner: Optional[AnyRunner] = None,
    ):
        SimAnalysis.__init__(self, circuit_file, runner)
        self.simulator = simulator
        self.resistors = self.editor.get_components("R")
        self.capacitors = self.editor.get_components("C")
        self.inductors = self.editor.get_components("L")
        self.diodes = self.editor.get_components("D")
        self.bipolars = self.editor.get_components("Q")
        self.mosfets = self.editor.get_components("M")
        self.subcircuits = self.editor.get_components("X")
        self.user_failure_modes: Dict[str, Dict[str, Any]] = OrderedDict()
        # Mapping of failure names to RunTask instances
        self.failure_simulations: Dict[str, Optional[RunTask]] = {}

    def add_failure_circuit(
        self, component: str, sub_circuit: Union[str, BaseEditor]
    ) -> None:
        if not component.startswith("X"):
            raise RuntimeError(
                "The failure modes addition only works with sub circuits"
            )
        if component not in self.subcircuits:
            raise ComponentNotFoundError()
        _ = sub_circuit
        raise NotImplementedError("TODO")  # TODO: Implement this

    def add_failure_mode(
        self, component: str, short_pins: Iterable[str], open_pins: Iterable[str]
    ) -> None:
        if not component.startswith("X"):
            raise RuntimeError("The failure modes addition only works with subcircuits")
        if component not in self.subcircuits:
            raise ComponentNotFoundError()
        _ = short_pins
        _ = open_pins
        raise NotImplementedError("TODO")  # TODO: Implement this

    def run_all(self) -> None:
        for resistor in self.resistors:
            # Short Circuit: set near-zero resistance
            self.editor.set_component_value(resistor, "1f")
            self.failure_simulations[f"{resistor}_S"] = self.run()
            # Open Circuit: remove component
            self.editor.remove_component(resistor)
            self.failure_simulations[f"{resistor}_O"] = self.run()
            self.editor.reset_netlist()

        for two_pin_comps in (self.capacitors, self.inductors, self.diodes):
            for two_pin_component in two_pin_comps:
                cinfo = self.editor.get_component(two_pin_component)
                # Open Circuit: remove component
                self.editor.remove_component(two_pin_component)
                self.failure_simulations[f"{two_pin_component}_O"] = self.run()
                # Short Circuit: insert short resistor
                netlist = getattr(self.editor, "netlist")
                netlist[
                    cinfo["line"]
                ] = f"Rfmea_short_{two_pin_component}{cinfo['nodes']} 1f"
                self.failure_simulations[f"{two_pin_component}_S"] = self.run()
                self.editor.reset_netlist()
