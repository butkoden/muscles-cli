import json

from muscles.cli.tooling import main
from muscles.cli import tooling


def test_machine_mode_uses_stderr_for_errors(capsys):
    code = main(["--machine", "inspect", "--app", "bad-entrypoint"])
    assert code == tooling.EXIT_INVALID_ARGUMENT
    out = capsys.readouterr()
    assert out.out.strip() == ""
    payload = json.loads(out.err)
    assert payload["status"] == "error"
    assert payload["error"]["type"] == "ValueError"


def test_ai_first_smoke_workflow(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    assert main(["--machine", "new", "demo", "--runtime", "asgi"]) == tooling.EXIT_SUCCESS
    new_payload = json.loads(capsys.readouterr().out)
    assert new_payload["status"] == "ok"

    monkeypatch.chdir(tmp_path / "demo")

    assert main(["--machine", "generate", "resource", "Booking", "--with-tests"]) == tooling.EXIT_SUCCESS
    gen_payload = json.loads(capsys.readouterr().out)
    assert "app/api/booking.py" in gen_payload["generated"]

    assert main(["--machine", "inspect", "--json"]) == tooling.EXIT_SUCCESS
    inspect_payload = json.loads(capsys.readouterr().out)
    assert inspect_payload["contract_version"] == "1"

    assert main(["--machine", "doctor", "--json"]) == tooling.EXIT_SUCCESS
    doctor_payload = json.loads(capsys.readouterr().out)
    assert doctor_payload["errors"] == []

    assert main(["--machine", "test"]) == tooling.EXIT_SUCCESS


def test_exit_codes_for_core_commands(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["--machine", "capabilities"]) == tooling.EXIT_SUCCESS
    assert main(["capabilities", "--quiet"]) == tooling.EXIT_SUCCESS

    assert main(["--machine", "new", "demo-project", "--runtime", "asgi"]) == tooling.EXIT_SUCCESS
    monkeypatch.chdir(tmp_path / "demo-project")

    monkeypatch.setattr(tooling, "run_project_tests", lambda *args, **kwargs: 1)
    assert main(["--machine", "test"]) == 1


def test_exit_code_invalid_for_non_project(tmp_path, monkeypatch):
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.chdir(empty)
    assert main(["--machine", "doctor"]) == tooling.EXIT_INVALID_ARGUMENT
