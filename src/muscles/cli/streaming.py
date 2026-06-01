from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any, TextIO

from muscles.core import stream_events


@dataclass(frozen=True)
class CliStreamRenderResult:
    exit_code: int
    events: list[dict[str, Any]]


def render_stream_result(
    stream_result: Any,
    *,
    json_lines: bool = False,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> CliStreamRenderResult:
    out = stdout or sys.stdout
    err = stderr or sys.stderr
    rendered: list[dict[str, Any]] = []
    exit_code = 0

    for event in stream_events(stream_result):
        payload = {
            "event": event.type,
            "data": event.data,
            "id": event.event_id,
            "metadata": dict(event.metadata),
        }
        rendered.append(payload)
        if json_lines:
            out.write(json.dumps(payload, ensure_ascii=False) + "\n")
            continue
        if event.type == "progress":
            out.write(f"progress: {event.data}\n")
        elif event.type == "log":
            out.write(f"log: {event.data}\n")
        elif event.type == "result":
            out.write(f"result: {event.data}\n")
        elif event.type == "error":
            exit_code = 1
            err.write(f"error: {event.data}\n")

    return CliStreamRenderResult(exit_code=exit_code, events=rendered)
