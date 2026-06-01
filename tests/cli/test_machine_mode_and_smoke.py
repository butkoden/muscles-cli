import json

from muscles.cli.tooling import main


def test_machine_mode_uses_stderr_for_errors(capsys):
    code = main(["--machine", "inspect", "--app", "bad-entrypoint"])
    assert code == 2
    out = capsys.readouterr()
    assert out.out.strip() == ""
    payload = json.loads(out.err)
    assert payload["status"] == "error"
    assert payload["error"]["type"] == "ValueError"


def test_ai_first_smoke_workflow(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    assert main(["--machine", "new", "demo", "--runtime", "asgi"]) == 0
    new_payload = json.loads(capsys.readouterr().out)
    assert new_payload["status"] == "ok"

    monkeypatch.chdir(tmp_path / "demo")

    assert main(["--machine", "generate", "resource", "Booking", "--with-tests"]) == 0
    gen_payload = json.loads(capsys.readouterr().out)
    assert "app/api/booking.py" in gen_payload["generated"]

    assert main(["--machine", "inspect", "--json"]) == 0
    inspect_payload = json.loads(capsys.readouterr().out)
    assert inspect_payload["contract_version"] == "1"

    assert main(["--machine", "doctor", "--json"]) == 0
    doctor_payload = json.loads(capsys.readouterr().out)
    assert doctor_payload["errors"] == []

    assert main(["--machine", "test"]) == 0

