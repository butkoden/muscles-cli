import json

from muscles.cli.tooling import build_capabilities_payload


def test_capabilities_payload_contains_contract_and_commands(monkeypatch):
    monkeypatch.setenv("MUSCLES_ENV", "development")
    payload = build_capabilities_payload()

    assert payload["capabilities_contract_version"] == "1"
    assert payload["framework"] == "Muscles"
    assert payload["runtime_mode"] == "development"
    assert payload["performance_contract"]["di_signature_cached"] is True

    names = [item["name"] for item in payload["commands"]]
    for required in ("new", "inspect", "action", "doctor", "generate", "test", "capabilities"):
        assert required in names


def test_capabilities_payload_command_safety_shape():
    payload = build_capabilities_payload()
    command = next(item for item in payload["commands"] if item["name"] == "generate")

    assert command["mutating"] is True
    assert command["dev_only"] is True
    assert "production_safe" in command


def test_capabilities_payload_is_json_serializable():
    payload = build_capabilities_payload()
    dumped = json.dumps(payload)
    loaded = json.loads(dumped)
    assert loaded["framework"] == "Muscles"
