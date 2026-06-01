from __future__ import annotations

import argparse
import importlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from muscles.core import inspect_application
from muscles.core import resolve_runtime_mode
from muscles.core import GenerationRequest
from .providers import default_generator_registry

APP_TEMPLATE = """from muscles import ApplicationMeta, Configurator, Context
from muscles.{runtime} import {strategy}


class App(metaclass=ApplicationMeta):
    config = Configurator(obj={{"main": {{"HOST": "0.0.0.0", "PORT": "8080"}}}})
    context = Context({strategy}, {{}})

    def run(self, *args):
        return self.context.execute(*args, shutup=True)
"""

CLI_APP_TEMPLATE = """from muscles import ApplicationMeta, Context
from muscles.cli import CliStrategy, cli


class App(metaclass=ApplicationMeta):
    context = Context(CliStrategy, {{}})

    def run(self, *args):
        return self.context.execute(*args, shutup=True)


@cli.group()
def bookings(*args):
    return True


@bookings.command(command_name="list")
def list_bookings(*args):
    return "ok"
"""

README_TEMPLATE = """# {project_name}

Generated with `muscles new`.

## Install

See canonical install matrix:
https://github.com/butkoden/muscles/blob/master/docs/installation.md

## Test

```bash
PYTHONPATH=. python -m pytest -q
```
"""

TEST_TEMPLATE = """def test_smoke():
    assert True
"""

PYPROJECT_TEMPLATE = """[build-system]
requires = ["setuptools>=69.0.2"]
build-backend = "setuptools.build_meta"

[project]
name = "{project_slug}"
version = "0.1.0"
description = "Generated Muscles project"
requires-python = ">=3.9"
dependencies = [
  "muscles",
]
"""

DOCKERFILE_TEMPLATE = """FROM python:3.12-slim
WORKDIR /app
COPY . .
CMD ["python", "-m", "pytest", "-q"]
"""

DOCKER_COMPOSE_TEMPLATE = """services:
  app:
    build: .
    command: python -m pytest -q
"""


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def scaffold_project(target: Path, runtime: str = "asgi", force: bool = False) -> list[str]:
    runtime = runtime.lower()
    if runtime not in {"asgi", "wsgi", "cli", "full"}:
        raise ValueError(f"Unsupported runtime `{runtime}`")

    if target.exists() and any(target.iterdir()) and not force:
        raise FileExistsError(f"Target directory `{target}` is not empty. Use --force to overwrite.")

    if target.exists() and force:
        for entry in target.iterdir():
            if entry.is_dir():
                shutil.rmtree(entry)
            else:
                entry.unlink()

    target.mkdir(parents=True, exist_ok=True)
    app_dir = target / "app"

    dirs = [
        app_dir / "domain",
        app_dir / "schemas",
        app_dir / "web",
        app_dir / "api",
        app_dir / "cli",
        app_dir / "rules",
        app_dir / "templates",
        app_dir / "static",
        target / "tests",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    strategy = {"asgi": "AsgiStrategy", "wsgi": "WsgiStrategy", "full": "WsgiStrategy"}.get(runtime)
    app_runtime = {"asgi": "asgi", "wsgi": "wsgi", "full": "wsgi"}.get(runtime)

    if runtime == "cli":
        application = CLI_APP_TEMPLATE
    else:
        application = APP_TEMPLATE.format(runtime=app_runtime, strategy=strategy)

    _write(app_dir / "__init__.py", "")
    _write(app_dir / "application.py", application)
    _write(app_dir / "config.py", "APP_ENV = 'development'\n")
    _write(target / "tests" / "test_smoke.py", TEST_TEMPLATE)
    _write(target / "README.md", README_TEMPLATE.format(project_name=target.name))
    _write(target / ".gitignore", "__pycache__/\n.pytest_cache/\n*.pyc\n")
    _write(target / "pyproject.toml", PYPROJECT_TEMPLATE.format(project_slug=target.name.replace("_", "-")))

    if runtime in {"asgi", "wsgi", "full"}:
        _write(target / "Dockerfile", DOCKERFILE_TEMPLATE)
        _write(target / "docker-compose.yml", DOCKER_COMPOSE_TEMPLATE)

    created = []
    for p in sorted(target.rglob("*")):
        if p.is_file():
            created.append(str(p.relative_to(target)))
    return created


def generate_artifact(
    project_root: Path,
    generator_type: str,
    name: str,
    force: bool = False,
    with_tests: bool = True,
) -> list[str]:
    app_dir = project_root / "app"
    if not app_dir.exists():
        raise FileNotFoundError("Muscles project not detected: `app/` directory is missing.")

    generator_type = generator_type.lower()
    registry = default_generator_registry()
    provider = registry.resolve(generator_type)
    return provider.generate(
        project_root=project_root,
        request=GenerationRequest(
            generator_type=generator_type,
            name=name,
            force=force,
            with_tests=with_tests,
        ),
    )


def detect_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in [current] + list(current.parents):
        if (candidate / "app").exists() and (candidate / "tests").exists():
            return candidate
    raise FileNotFoundError("Muscles project root not found.")


def run_doctor(project_root: Path) -> dict:
    errors = []
    warnings = []

    if not (project_root / "app").exists():
        errors.append(
            {
                "severity": "error",
                "code": "MISSING_APP_DIR",
                "message": "Directory `app/` is missing.",
                "suggested_fix": "Run `muscles new <name>` or restore `app/`.",
            }
        )
    if not (project_root / "tests").exists():
        errors.append(
            {
                "severity": "error",
                "code": "MISSING_TESTS_DIR",
                "message": "Directory `tests/` is missing.",
                "suggested_fix": "Add tests directory and baseline tests.",
            }
        )
    else:
        test_files = list((project_root / "tests").glob("test_*.py"))
        if len(test_files) == 0:
            errors.append(
                {
                    "severity": "error",
                    "code": "MISSING_TESTS",
                    "message": "No test files matching tests/test_*.py.",
                    "suggested_fix": "Generate tests or add smoke/unit tests.",
                }
            )

    config_path = project_root / "app" / "config.py"
    if config_path.exists():
        body = config_path.read_text(encoding="utf-8")
        if "TODO" in body:
            warnings.append(
                {
                    "severity": "warning",
                    "code": "CONFIG_TODO",
                    "message": "Config contains TODO markers.",
                    "suggested_fix": "Resolve placeholders in app/config.py.",
                }
            )

    return {"errors": errors, "warnings": warnings, "info": []}


def run_project_tests(project_root: Path) -> int:
    env = os.environ.copy()
    env["PYTHONPATH"] = "." + (os.pathsep + env["PYTHONPATH"] if "PYTHONPATH" in env else "")
    process = subprocess.run(
        ["python", "-m", "pytest", "-q"],
        cwd=str(project_root),
        env=env,
        check=False,
    )
    return process.returncode


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="muscles")
    parser.add_argument("--json", action="store_true", help="JSON output when supported")
    subparsers = parser.add_subparsers(dest="command")

    new_parser = subparsers.add_parser("new", help="Create a new Muscles project")
    new_parser.add_argument("project_name")
    new_parser.add_argument("--runtime", default="asgi", choices=["asgi", "wsgi", "cli", "full"])
    new_parser.add_argument("--force", action="store_true")

    capabilities_parser = subparsers.add_parser("capabilities", help="Show CLI and project capabilities")
    capabilities_parser.add_argument("--json", action="store_true", help="JSON output")

    generate_parser = subparsers.add_parser("generate", help="Generate Muscles artifacts")
    generate_parser.add_argument("generator_type", choices=["page", "api-resource", "cli-command", "value-object", "resource"])
    generate_parser.add_argument("name")
    generate_parser.add_argument("--force", action="store_true")
    generate_parser.add_argument("--with-tests", action="store_true")

    doctor_parser = subparsers.add_parser("doctor", help="Diagnose Muscles project")
    doctor_parser.add_argument("--json", action="store_true", help="JSON output")

    test_parser = subparsers.add_parser("test", help="Run canonical Muscles project tests")
    test_parser.add_argument("--doctor", action="store_true", help="Run doctor before tests")

    inspect_parser = subparsers.add_parser("inspect", help="Inspect Muscles application contract")
    inspect_parser.add_argument("--app", required=False, help="Entrypoint in module:ClassOrObject format")
    inspect_parser.add_argument("--json", action="store_true", help="JSON output")

    for command_name in ("actions", "routes", "schemas", "rules", "cli", "sql"):
        command_parser = subparsers.add_parser(command_name, help=f"Inspect {command_name}")
        command_parser.add_argument("--app", required=False, help="Entrypoint in module:ClassOrObject format")
        command_parser.add_argument("--json", action="store_true", help="JSON output")
    return parser


def load_app_from_entrypoint(entrypoint: str):
    if ":" not in entrypoint:
        raise ValueError("Entrypoint must use module:object format")
    module_name, object_name = entrypoint.split(":", 1)
    module = importlib.import_module(module_name)
    target = getattr(module, object_name)
    if isinstance(target, type):
        return target()
    return target


def build_inspection_payload(app=None, app_entrypoint: str | None = None) -> dict:
    if app is None and app_entrypoint:
        app = load_app_from_entrypoint(app_entrypoint)
    return inspect_application(app=app)


def build_capabilities_payload() -> dict:
    runtime_mode = resolve_runtime_mode().value
    commands = [
        {"name": "capabilities", "syntax": "muscles capabilities --json", "read_only": True, "mutating": False, "dev_only": False, "production_safe": True},
        {"name": "new", "syntax": "muscles new <project-name> --runtime asgi|wsgi|cli", "read_only": False, "mutating": True, "dev_only": True, "production_safe": False},
        {"name": "inspect", "syntax": "muscles inspect --json --app app.application:App", "read_only": True, "mutating": False, "dev_only": False, "production_safe": "redacted"},
        {"name": "doctor", "syntax": "muscles doctor --json", "read_only": True, "mutating": False, "dev_only": True, "production_safe": False},
        {"name": "generate", "syntax": "muscles generate resource <Name> --with-tests", "read_only": False, "mutating": True, "dev_only": True, "production_safe": False},
        {"name": "test", "syntax": "muscles test", "read_only": True, "mutating": False, "dev_only": False, "production_safe": True},
    ]
    return {
        "capabilities_contract_version": "1",
        "framework": "Muscles",
        "runtime_mode": runtime_mode,
        "project_detected": (Path.cwd() / "app").exists(),
        "commands": commands,
        "recommended_ai_workflow": [
            "muscles capabilities --json",
            "muscles inspect --json",
            "muscles generate ...",
            "muscles doctor --json",
            "muscles test",
        ],
        "ai_docs": [
            "docs/ai/AGENTS.md",
            "docs/ai/cursor-rules.md",
            "docs/ai/copilot-instructions.md",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "capabilities":
        payload = build_capabilities_payload()
        as_json = getattr(args, "json", False) or getattr(args, "json", False)
        if as_json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        print("Muscles capabilities")
        print(f"runtime_mode: {payload['runtime_mode']}")
        print("commands:")
        for item in payload["commands"]:
            print(f" - {item['name']}: {item['syntax']}")
        return 0

    if args.command in {"inspect", "actions", "routes", "schemas", "rules", "cli", "sql"}:
        payload = build_inspection_payload(app_entrypoint=getattr(args, "app", None))
        if args.command == "inspect":
            data = payload
        elif args.command == "actions":
            data = {"actions": payload.get("actions", [])}
        elif args.command == "routes":
            data = {"routes": payload.get("routes", [])}
        elif args.command == "schemas":
            data = {"schemas": payload.get("schemas", [])}
        elif args.command == "rules":
            data = {"rules": payload.get("rules", [])}
        elif args.command == "sql":
            data = {"sql": payload.get("sql", [])}
        else:
            data = {"cli": payload.get("cli", payload.get("commands", []))}

        if getattr(args, "json", False):
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print(data)
        return 0

    if args.command == "generate":
        generated = generate_artifact(
            project_root=Path.cwd(),
            generator_type=args.generator_type,
            name=args.name,
            force=args.force,
            with_tests=args.with_tests,
        )
        print("Generated files:")
        for item in generated:
            print(f" - {item}")
        print("Next steps:")
        print("  muscles inspect --json")
        print("  muscles test")
        return 0

    if args.command == "doctor":
        root = detect_project_root()
        report = run_doctor(root)
        if getattr(args, "json", False):
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(report)
        return 0 if len(report["errors"]) == 0 else 2

    if args.command == "test":
        root = detect_project_root()
        if getattr(args, "doctor", False):
            report = run_doctor(root)
            if len(report["errors"]) > 0:
                print("Doctor failed. Fix errors before test run.")
                print(json.dumps(report, ensure_ascii=False, indent=2))
                return 2
        return run_project_tests(root)

    if args.command != "new":
        if getattr(args, "json", False):
            help_payload = {
                "framework": "Muscles",
                "commands": ["new", "capabilities"],
                "status": "ok",
            }
            print(json.dumps(help_payload, ensure_ascii=False, indent=2))
            return 0
        parser.print_help()
        return 1

    target = Path.cwd() / args.project_name
    files = scaffold_project(target=target, runtime=args.runtime, force=args.force)
    print(f"Created project at: {target}")
    print("Generated files:")
    for file_name in files:
        print(f" - {file_name}")
    print("Next steps:")
    print(f"  cd {args.project_name}")
    print("  PYTHONPATH=. python -m pytest -q")
    return 0
