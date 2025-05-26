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
# Name:        process_callback.py
# Purpose:     Being able to execute callback in a separate process
#
# Author:      Nuno Brum (nuno.brum@gmail.com)
#
# Created:     23-04-2023
# Licence:     refer to the LICENSE file
# -------------------------------------------------------------------------------
""""""
from __future__ import annotations

from multiprocessing import Process, get_context
from multiprocessing.queues import Queue as MPQueue
from typing import Any


class ProcessCallback(Process):
    """Wrapper for the callback function."""

    def __init__(
            self,
            raw: str,
            log: str,
            group: Any = None,
            name: str | None = None,
            *,
            daemon: bool | None = None,
            **kwargs: Any) -> None:
        super().__init__(group=group, name=name, daemon=daemon)
        self.queue: MPQueue[Any] = MPQueue(ctx=get_context())
        self.raw_file = raw
        self.log_file = log
        self.kwargs = kwargs

    def run(self) -> None:
        ret = self.callback(self.raw_file, self.log_file, **self.kwargs)
        if ret is None:
            ret = "Callback doesn't return anything"
        self.queue.put(ret)

    @staticmethod
    def callback(raw_file: str, log_file: str, **kwargs: Any) -> Any:
        """This function needs to be overriden."""
        ...
