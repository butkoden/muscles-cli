import sys
from pathlib import Path

from muscles.cli.tooling import build_inspection_payload
from muscles.cli.tooling import load_app_from_entrypoint


def test_load_app_from_entrypoint(tmp_path, monkeypatch):
    pkg = tmp_path / "demoapp"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "app.py").write_text(
        "class App:\n"
        "    pass\n",
        encoding="utf-8",
    )

    monkeypatch.syspath_prepend(str(tmp_path))
    app = load_app_from_entrypoint("demoapp.app:App")
    assert app.__class__.__name__ == "App"


def test_build_inspection_payload_from_app():
    class FakeNode:
        key = "api.v1.ping"
        full_route = "/api/v1/ping"

    def ping():
        return "ok"

    ping.node = FakeNode()
    ping.method = "get"

    class FakeApp:
        __muscles_routes__ = [ping]

    payload = build_inspection_payload(app=FakeApp())
    assert payload["contract_version"] == "1"
    assert payload["routes"][0]["path"] == "/api/v1/ping"
