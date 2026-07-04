import json

from muscles.cli import tooling
from muscles.cli.tooling import main


def _write_demo_app(tmp_path, monkeypatch):
    pkg = tmp_path / "actiondemo"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "application.py").write_text(
        "from muscles import ApplicationMeta, BaseStrategy, Context\n"
        "\n"
        "class EchoStrategy(BaseStrategy):\n"
        "    def execute(self, *args, **kwargs):\n"
        "        return kwargs\n"
        "\n"
        "class App(metaclass=ApplicationMeta):\n"
        "    context = Context(EchoStrategy)\n"
        "\n"
        "app = App()\n"
        "\n"
        "@app.action(\n"
        "    name='bookings.echo',\n"
        "    input_schema={'type': 'object', 'properties': {'title': {'type': 'string'}}, 'required': ['title']},\n"
        "    transports=['cli'],\n"
        ")\n"
        "def echo(payload, context):\n"
        "    return {'payload': payload, 'transport': context.transport, 'metadata': context.metadata}\n"
        "\n"
        "@app.action(name='bookings.stream', input_schema={'type': 'object', 'properties': {}}, transports=['cli'])\n"
        "def stream(_payload, context):\n"
        "    yield {'event': 'progress', 'data': {'transport': context.transport}}\n"
        "    yield {'event': 'result', 'data': {'ok': True}}\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    return "actiondemo.application:App"


def test_action_list_outputs_registered_actions(tmp_path, monkeypatch, capsys):
    entrypoint = _write_demo_app(tmp_path, monkeypatch)

    code = main(["action", "list", "--app", entrypoint, "--json"])

    assert code == tooling.EXIT_SUCCESS
    payload = json.loads(capsys.readouterr().out)
    names = [item["name"] for item in payload["actions"]]
    assert "bookings.echo" in names
    assert "bookings.stream" in names


def test_action_inspect_outputs_single_action_contract(tmp_path, monkeypatch, capsys):
    entrypoint = _write_demo_app(tmp_path, monkeypatch)

    code = main(["action", "inspect", "bookings.echo", "--app", entrypoint, "--json"])

    assert code == tooling.EXIT_SUCCESS
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"]["name"] == "bookings.echo"
    assert payload["action"]["input_schema"]["required"] == ["title"]


def test_action_run_executes_core_dispatcher_with_cli_transport(tmp_path, monkeypatch, capsys):
    entrypoint = _write_demo_app(tmp_path, monkeypatch)

    code = main(
        [
            "action",
            "run",
            "bookings.echo",
            "--app",
            entrypoint,
            "--payload-json",
            '{"title": "Call"}',
            "--json",
        ]
    )

    assert code == tooling.EXIT_SUCCESS
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] == "bookings.echo"
    assert payload["result"]["payload"] == {"title": "Call"}
    assert payload["result"]["transport"] == "cli"
    assert payload["result"]["metadata"] == {"projection": "cli"}


def test_action_run_reads_payload_file(tmp_path, monkeypatch, capsys):
    entrypoint = _write_demo_app(tmp_path, monkeypatch)
    payload_file = tmp_path / "payload.json"
    payload_file.write_text('{"title": "From file"}', encoding="utf-8")

    code = main(
        [
            "action",
            "run",
            "bookings.echo",
            "--app",
            entrypoint,
            "--payload-file",
            str(payload_file),
            "--json",
        ]
    )

    assert code == tooling.EXIT_SUCCESS
    payload = json.loads(capsys.readouterr().out)
    assert payload["result"]["payload"] == {"title": "From file"}


def test_action_run_stream_outputs_json_lines(tmp_path, monkeypatch, capsys):
    entrypoint = _write_demo_app(tmp_path, monkeypatch)

    code = main(["action", "run", "bookings.stream", "--app", entrypoint, "--json-lines"])

    assert code == tooling.EXIT_SUCCESS
    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert [line["event"] for line in lines] == ["progress", "result"]
    assert lines[0]["data"] == {"transport": "cli"}


def test_action_run_validation_error_is_structured_json(tmp_path, monkeypatch, capsys):
    entrypoint = _write_demo_app(tmp_path, monkeypatch)

    code = main(["action", "run", "bookings.echo", "--app", entrypoint, "--payload-json", "{}", "--json"])

    assert code == tooling.EXIT_INVALID_ARGUMENT
    captured = capsys.readouterr()
    assert captured.out == ""
    payload = json.loads(captured.err)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "action_validation_error"
    assert payload["error"]["action"] == "bookings.echo"
    assert payload["error"]["data"]["path"] == []
