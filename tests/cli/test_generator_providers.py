from muscles.cli.providers import default_generator_registry


def test_default_generator_registry_contains_cli_command_provider():
    registry = default_generator_registry()
    provider = registry.resolve("cli-command")
    assert provider.name == "cli-command"


def test_default_generator_registry_resolves_resource_provider():
    registry = default_generator_registry()
    provider = registry.resolve("resource")
    assert provider.name == "core"

