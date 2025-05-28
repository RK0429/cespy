#!/usr/bin/env python
# coding=utf-8
"""XML-RPC server for distributed SPICE simulation execution.

This module implements a simulation server that accepts client requests via XML-RPC,
manages simulation sessions, executes simulations in parallel, and returns results
to clients in a compressed format.
"""

import io
import logging
import threading
import uuid
import zipfile
from pathlib import Path
from typing import List, Tuple, Type
from xmlrpc.client import Binary
from xmlrpc.server import SimpleXMLRPCServer

from cespy.client_server.srv_sim_runner import ServerSimRunner
from cespy.sim.simulator import Simulator

_logger = logging.getLogger("cespy.SimServer")


class SimServer:
    """This class implements a server that can run simulations by request of a client
    located in a different machine.

    The server is implemented using the SimpleXMLRPCServer class from the xmlrpc.server
    module.

    The client can request the server to start a session, run a simulation, check the
    status of the simulations and retrieve the results of the simulations. The server
    can run multiple simulations in parallel, but the number of parallel simulations is
    limited by the parallel_sims parameter.

    The server can be stopped by the client by calling the stop_server method.

    :param simulator: The simulator to be used. It must be a class that derives from the
        BaseSimulator class.
    :param parallel_sims: The maximum number of parallel simulations that the server can
        run. Default is 4.
    :param output_folder: The folder where the results of the simulations will be
        stored. Default is './temp'
    :param timeout: The maximum time that a simulation can run. Default is None, which
        means that there is no timeout.
    :param port: The port where the server will listen for requests. Default is 9000
    """

    def __init__(
        self,
        simulator: Type[Simulator],
        parallel_sims: int = 4,
        output_folder: str = "./temp",
        timeout: float = 300,
        port: int = 9000,
        host: str = "localhost",
    ) -> None:
        self.output_folder = output_folder
        self.simulation_manager: ServerSimRunner = ServerSimRunner(
            parallel_sims=parallel_sims,
            timeout=timeout,
            verbose=False,
            output_folder=output_folder,
            simulator=simulator,
        )
        self.server = SimpleXMLRPCServer(
            (host, port),
            # requestHandler=RequestHandler
        )
        self.server.register_introspection_functions()
        self.server.register_instance(self)
        # this will contain the session_id ids hashing their respective list of
        # sim_tasks
        self.sessions: dict[str, list[int]] = {}
        self.simulation_manager.start()
        self.server_thread = threading.Thread(
            target=self.server.serve_forever, name="ServerThread"
        )
        self.server_thread.start()

    def add_sources(self, session_id: str, zip_data: Binary) -> bool:
        """Add sources to the simulation.

        The sources are contained in a zip file will be added to the simulation folder.
        Returns True if the sources were added and False if the session_id is not valid.
        """
        _logger.info("Server: Add sources %s", session_id)
        if session_id not in self.sessions:
            return False  # This indicates that no job is started
        # Create a buffer from the zip data
        zip_buffer = io.BytesIO(zip_data.data)
        _logger.debug("Server: Created the buffer")
        # Extract the contents of the zip file
        answer = False
        with zipfile.ZipFile(zip_buffer, "r") as zip_file:
            for name in zip_file.namelist():
                _logger.debug("Server: Writing %s to zip file", name)
            if len(zip_file.namelist()) >= 0:
                zip_file.extractall(self.output_folder)
                answer = True
        return answer

    def run(self, session_id: str, circuit_name: str, zip_data: Binary) -> int:
        """Run a simulation for the given session.

        Args:
            session_id: The session identifier
            circuit_name: Name of the circuit file
            zip_data: Binary data containing the circuit and dependencies

        Returns:
            The run number of the simulation or -1 if failed
        """
        _logger.info("Server: Run %s : %s", session_id, circuit_name)
        if not self.add_sources(session_id, zip_data):
            return -1

        circuit_path = Path(self.output_folder) / circuit_name
        _logger.info("Server: Running simulation of %s", circuit_path)
        runno = self.simulation_manager.add_simulation(circuit_path)
        if runno != -1:
            self.sessions[session_id].append(runno)
        return runno

    def start_session(self) -> str:
        """Returns an unique key that represents the session.

        It will be later used to sort the sim_tasks belonging to the session.
        """
        session_id = str(
            uuid.uuid4()
        )  # Needs to be a string, otherwise the rpc client can't handle it
        _logger.info("Server: Starting session %s", session_id)
        self.sessions[session_id] = []
        return session_id

    def status(self, session_id: str) -> List[int]:
        """Returns a dictionary with task information. The key for the dictionary is the
        simulation identifier returned by the simulation start command. The value
        associated with each simulation identifier is another dictionary containing the
        following keys:

        * 'completed' - whether the simulation is already finished

        * 'start' - time when the simulation was started

        * 'stop' - server time
        """
        _logger.debug("Server: collecting status for %s", session_id)
        ret = []
        for task_info in self.simulation_manager.completed_tasks:
            _logger.debug(task_info)
            runno = task_info["runno"]
            if runno in self.sessions[session_id]:
                ret.append(
                    runno
                )  # transfers the dictionary from the simulation_manager completed task
                # to the return dictionary
        _logger.debug("Server: Returning status %s", ret)
        return ret

    def get_files(self, session_id: str, runno: int) -> Tuple[str, Binary]:
        if runno in self.sessions[session_id]:
            for task_info in self.simulation_manager.completed_tasks:
                if runno == task_info["runno"]:
                    # Create a buffer to store the zip file in memory
                    zip_file = task_info["zipfile"]
                    zip_handle = zip_file.open("rb")
                    # Read the zip file from the buffer and send it to the server
                    zip_data = zip_handle.read()
                    zip_handle.close()
                    self.simulation_manager.erase_files_of_runno(runno)
                    return zip_file.name, Binary(zip_data)

        return "", Binary(b"")  # Returns and empty data

    def close_session(self, session_id: str) -> bool:
        """Cleans all the pending sim_tasks with."""
        if session_id not in self.sessions:
            return False
        _logger.info("Closing session %s", session_id)
        for runno in self.sessions[session_id]:
            self.simulation_manager.erase_files_of_runno(runno)
        del self.sessions[session_id]
        return True  # Needs to return always something. None is not supported

    def stop_server(self) -> bool:
        _logger.debug("Server: stopping...ServerInterface")
        self.simulation_manager.stop()
        self.server.shutdown()
        _logger.info("Server: stopped...ServerInterface")
        return True  # Needs to return always something. None is not supported

    def running(self) -> bool:
        return self.simulation_manager.running()
