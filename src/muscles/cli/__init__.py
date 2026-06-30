from .cli import Colors
from .cli import Command
from .cli import Argument
from .cli import Group
from .cli import Console
from .cli import cli
from .cli import argsparse
from .cli import CliStrategy
from .cli import ConsoleErrorHandler
from .streaming import CliStreamRenderResult
from .streaming import render_stream_result


_TOOLING_EXPORTS = {
    "scaffold_project",
    "main",
    "build_capabilities_payload",
    "load_app_from_entrypoint",
    "build_inspection_payload",
    "generate_artifact",
    "detect_project_root",
    "run_doctor",
    "run_project_tests",
}


def __getattr__(name):
    if name in _TOOLING_EXPORTS:
        import importlib

        tooling = importlib.import_module(".tooling", __name__)
        return getattr(tooling, name)
    raise AttributeError(name)


__all__ = (
    "Colors",
    "Command",
    "Argument",
    "Group",
    "Console",
    "cli",
    "argsparse",
    "CliStrategy",
    "ConsoleErrorHandler",
    "scaffold_project",
    "build_capabilities_payload",
    "load_app_from_entrypoint",
    "build_inspection_payload",
    "generate_artifact",
    "detect_project_root",
    "run_doctor",
    "run_project_tests",
    "CliStreamRenderResult",
    "render_stream_result",
    "main",
)
