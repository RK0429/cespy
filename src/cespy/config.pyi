from __future__ import annotations

from pathlib import Path
from typing import Any

class SimulatorConfig:
    executable_path: str | None
    library_paths: list[str]
    default_timeout: float
    wine_prefix: str | None
    environment: dict[str, str]
    command_line_args: list[str]

    def merge(self, other: SimulatorConfig) -> None: ...


class ServerConfig:
    host: str
    port: int
    timeout: float
    max_retries: int
    retry_delay: float
    max_parallel_jobs: int
    output_folder: str


class CespyConfig:
    default_encoding: str
    default_timeout: float
    parallel_sims: int
    log_level: str
    debug_mode: bool
    output_folder: str
    temp_folder: str | None
    auto_cleanup: bool
    max_output_size: int
    use_wine: bool
    wine_prefix: str | None
    force_windows_paths: bool
    simulators: dict[str, SimulatorConfig]
    server: ServerConfig
    process_poll_interval: float
    enable_profiling: bool
    cache_parsed_files: bool

    def __post_init__(self) -> None: ...
    def get_simulator_config(self, simulator: str) -> SimulatorConfig: ...
    def update_from_dict(self, config_dict: dict[str, Any]) -> None: ...
    def to_dict(self) -> dict[str, Any]: ...
    def save(self, filepath: str | Path) -> None: ...

    @classmethod
    def from_file(cls, filepath: str | Path) -> CespyConfig: ...
    @classmethod
    def from_environment(cls) -> CespyConfig: ...


def get_config() -> CespyConfig: ...

def set_config(config: CespyConfig) -> None: ...

def load_config(filepath: str | Path | None = None) -> CespyConfig: ...
