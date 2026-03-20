from __future__ import annotations

from .__about__ import DISTRIBUTION_NAME, MODULE_NAME, PACKAGE_NAME, SCAFFOLD_VERSION, __version__
from .api import (
    build_agent_memory,
    build_agent_memory_snapshot,
    derive_agent_memory_path,
    discover_agent_memory_paths,
    load_agent_memory,
    persist_agent_memory,
    read_agent_memory,
    run_agent_memory_benchmark,
    validate_project_pack,
    write_agent_memory,
)
from .cli import main

__all__ = [
    "DISTRIBUTION_NAME",
    "MODULE_NAME",
    "PACKAGE_NAME",
    "SCAFFOLD_VERSION",
    "__version__",
    "build_agent_memory",
    "build_agent_memory_snapshot",
    "derive_agent_memory_path",
    "discover_agent_memory_paths",
    "load_agent_memory",
    "persist_agent_memory",
    "read_agent_memory",
    "run_agent_memory_benchmark",
    "validate_project_pack",
    "write_agent_memory",
    "main",
]
