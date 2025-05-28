#!/usr/bin/env python
# coding=utf-8

import argparse
import logging
import sys
import time
from typing import Type

try:
    import keyboard
except ImportError:
    # keyboard module is optional and only needed for interactive server control
    keyboard = None

from cespy.client_server.sim_server import SimServer
from cespy.simulators.ltspice_simulator import LTspice
from cespy.simulators.ngspice_simulator import NGspiceSimulator
from cespy.simulators.xyce_simulator import XyceSimulator


def main() -> None:
    # declare simulator variable with default
    simulator: Type[LTspice] | Type[NGspiceSimulator] | Type[XyceSimulator] = LTspice
    parser = argparse.ArgumentParser(
        description="Run the SPICE server with specified simulator (LTSpice, NGSpice, XYCE)."
    )
    parser.add_argument(
        "simulator",
        type=str,
        help="Simulator to be used ('LTSpice', 'NGSpice', 'XYCE')",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=9000,
        help="Port to run the server. Default is 9000",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=".",
        help="Output folder for the results. Default is current folder",
    )
    parser.add_argument(
        "-l",
        "--parallel",
        type=int,
        default=4,
        help="Maximum number of parallel simulations. Default is 4",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=300,
        help="Timeout for the simulations in seconds. Default is 300",
    )

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    if args.parallel < 1:
        args.parallel = 1

    sim_key = args.simulator.lower()
    if sim_key == "ltspice":
        simulator = LTspice
    elif sim_key == "ngspice":
        simulator = NGspiceSimulator
    elif sim_key == "xyce":
        simulator = XyceSimulator
    else:
        parser.error(f"Unsupported simulator '{args.simulator}'")

    print("Starting Server")
    server = SimServer(
        simulator=simulator,
        parallel_sims=args.parallel,
        output_folder=args.output,
        timeout=args.timeout,
        port=args.port,
    )
    print("Server Started. Press and hold 'q' to stop")
    while server.running():
        time.sleep(0.2)
        if keyboard and keyboard.is_pressed("q"):
            server.stop_server()
            break


if __name__ == "__main__":
    log1 = logging.getLogger("cespy.ServerSimRunner")
    log2 = logging.getLogger("cespy.SimServer")
    log3 = logging.getLogger("cespy.SimRunner")
    log4 = logging.getLogger("cespy.RunTask")
    log1.setLevel(logging.INFO)
    log2.setLevel(logging.INFO)
    log3.setLevel(logging.INFO)
    log4.setLevel(logging.INFO)
    main()
