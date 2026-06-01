from pathlib import Path

import pytest

from muscles.cli.tooling import scaffold_project


def test_scaffold_asgi_project(tmp_path):
    target = tmp_path / "demo-asgi"
    files = scaffold_project(target=target, runtime="asgi", force=False)

    assert (target / "app" / "application.py").exists()
    assert (target / "app" / "api").is_dir()
    assert (target / "tests" / "test_smoke.py").exists()
    assert (target / "Dockerfile").exists()
    assert (target / "docker-compose.yml").exists()
    assert "README.md" in files


def test_scaffold_wsgi_project(tmp_path):
    target = tmp_path / "demo-wsgi"
    scaffold_project(target=target, runtime="wsgi", force=False)

    assert (target / "app" / "application.py").exists()
    assert (target / "Dockerfile").exists()
    assert (target / "docker-compose.yml").exists()


def test_scaffold_cli_project(tmp_path):
    target = tmp_path / "demo-cli"
    scaffold_project(target=target, runtime="cli", force=False)

    assert (target / "app" / "cli").is_dir()
    assert (target / "app" / "api").is_dir()
    assert not (target / "Dockerfile").exists()
    assert not (target / "docker-compose.yml").exists()


def test_scaffold_fails_on_non_empty_without_force(tmp_path):
    target = tmp_path / "demo"
    target.mkdir(parents=True, exist_ok=True)
    (target / "old.txt").write_text("legacy", encoding="utf-8")

    with pytest.raises(FileExistsError):
        scaffold_project(target=target, runtime="asgi", force=False)


def test_scaffold_force_allows_existing_directory(tmp_path):
    target = tmp_path / "demo"
    target.mkdir(parents=True, exist_ok=True)
    (target / "old.txt").write_text("legacy", encoding="utf-8")

    scaffold_project(target=target, runtime="asgi", force=True)
    assert (target / "app" / "application.py").exists()


def test_generated_application_uses_muscles_imports(tmp_path):
    target = tmp_path / "demo"
    scaffold_project(target=target, runtime="asgi", force=False)
    body = (target / "app" / "application.py").read_text(encoding="utf-8")
    assert "from muscles import ApplicationMeta, Configurator, Context" in body
