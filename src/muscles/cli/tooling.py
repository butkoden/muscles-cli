from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import re
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
    context = Context({strategy}, params={{}})

    def run(self, *args):
        return self.context.execute(*args, shutup=True)
"""

CLI_APP_TEMPLATE = """from muscles import ApplicationMeta, Context
from muscles.cli import CliStrategy, cli


class App(metaclass=ApplicationMeta):
    context = Context(CliStrategy, params={{}})

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


EXIT_SUCCESS = 0
EXIT_INVALID_ARGUMENT = 2
EXIT_RUNTIME_ERROR = 1


_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


AI_DSL_CHEAT_SHEET = """AI-friendly command DSL:
- action: API action name, e.g. `bookings.inspect`, `health.check`
- transport: execution transport (`asgi`, `wsgi`, `cli`, `full`)
- context: `Context(...)` in App settings
- rule: validation/route/parse rule name
- schema: data schema class in request/response
- resource: route prefix object (for domain groups)
- query: list-like command to fetch many entries
- status: command outcome (`ok`, `warn`, `error`)
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


def _entrypoint_candidates(project_root: Path) -> list[str]:
    return [
        "app.application:App",
        "app.app:App",
        "app.main:App",
        "app.__init__:App",
    ]


def _load_project_app(project_root: Path):
    sys.path.insert(0, str(project_root))
    last_error = None
    for entrypoint in _entrypoint_candidates(project_root):
        try:
            return load_app_from_entrypoint(entrypoint)
        except Exception as exc:  # pragma: no cover - defensive only
            last_error = exc
            continue
    raise last_error or ValueError("No runnable app entrypoint found.")


def _has_nested_cli_options(cli_root: Path) -> bool:
    for path in cli_root.glob("**/*.py"):
        content = path.read_text(encoding="utf-8")
        if ".group(" in content and ".argument(" in content:
            return True
    return False


def _has_map_model_autoincrement(sql_root: Path) -> bool:
    for path in sql_root.glob("**/*.py"):
        content = path.read_text(encoding="utf-8")
        if "map_model(" in content and "Integer(" in content and "autoincrement" in content:
            return True
    return False


def _has_otel_hooks(project_root: Path) -> bool:
    for path in project_root.glob("**/*.py"):
        if path.name.startswith("."):
            continue
        content = path.read_text(encoding="utf-8")
        if (
            "opentelemetry" in content.lower()
            or "otel" in content.lower()
            or "from muscles import Watchdog" in content
            or "Watchdog" in content
        ):
            return True
    return False


def _collect_diagnostic_checks(payload: dict, check_key: str, status: str, message: str, code: str):
    root_check = payload.setdefault("checks", {})
    root_check[check_key] = {
        "status": status,
        "message": message,
        "code": code,
    }

def run_doctor(project_root: Path) -> dict:
    errors = []
    warnings = []
    checks = {}
    info = []

    if not (project_root / "app").exists():
        errors.append(
            {
                "severity": "error",
                "code": "MISSING_APP_DIR",
                "message": "Directory `app/` is missing.",
                "suggested_fix": "Run `muscles new <name>` or restore `app/`.",
            }
        )
        _collect_diagnostic_checks(checks, "routes", "fail", "app directory missing", "DOCS_ROUTES")
    else:
        _collect_diagnostic_checks(checks, "routes", "ok", "app directory exists", "DOCS_ROUTES")

    if not (project_root / "tests").exists():
        errors.append(
            {
                "severity": "error",
                "code": "MISSING_TESTS_DIR",
                "message": "Directory `tests/` is missing.",
                "suggested_fix": "Add tests directory and baseline tests.",
            }
        )
        _collect_diagnostic_checks(checks, "tests", "fail", "tests directory missing", "DOCS_TESTS")
    else:
        _collect_diagnostic_checks(checks, "tests", "ok", "tests directory exists", "DOCS_TESTS")
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
            _collect_diagnostic_checks(checks, "tests", "fail", "no test_*.py files found", "DOCS_TESTS_CONTENT")
        else:
            _collect_diagnostic_checks(checks, "tests", "ok", f"found {len(test_files)} test files", "DOCS_TESTS_CONTENT")

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
            _collect_diagnostic_checks(checks, "config", "warn", "TODO marker in config", "DOCS_CONFIG")
        else:
            _collect_diagnostic_checks(checks, "config", "ok", "config parsed", "DOCS_CONFIG")

    try:
        app = _load_project_app(project_root)
        payload = build_inspection_payload(app=app)
        routes = payload.get("routes", [])
        path_map = [item.get("path") for item in routes]
        route_contract = payload.get("route_contract", {}).get("canonical", {})
        required_canonical = set(route_contract.values())
        missing_canonical = sorted(required_canonical - set(path_map))
        if missing_canonical:
            errors.append(
                {
                    "severity": "error",
                    "code": "MISSING_CANONICAL_ROUTES",
                    "message": f"Missing canonical routes: {', '.join(missing_canonical)}",
                    "suggested_fix": "Enable rest API middleware or add routes manually.",
                }
            )
            _collect_diagnostic_checks(checks, "routing", "fail", "some canonical routes are missing", "DOCS_ROUTING")
        else:
            _collect_diagnostic_checks(checks, "routing", "ok", "canonical routes found", "DOCS_ROUTING")

        route_aliases = payload.get("route_contract", {}).get("aliases", {})
        missing_aliases: list[str] = []
        for alias, canonical in route_aliases.items():
            if canonical not in path_map:
                errors.append(
                    {
                        "severity": "error",
                        "code": "MISSING_CANONICAL_ALIAS_TARGET",
                        "message": f"Canonical target missing for alias {alias}: {canonical}",
                        "suggested_fix": "Check RestApi route contract setup.",
                    }
                )
            if alias not in path_map:
                warnings.append(
                    {
                        "severity": "warning",
                        "code": "MISSING_ALIAS_ROUTE",
                        "message": f"Compatibility alias missing: {alias} -> {canonical}",
                        "suggested_fix": "Keep compatibility aliases until migration is complete.",
                    }
                )
                missing_aliases.append(alias)
        _collect_diagnostic_checks(
            checks,
            "route_aliases",
            "ok" if len(missing_aliases) == 0 else "warn",
            "all compatibility aliases found" if len(missing_aliases) == 0 else "compatibility aliases missing",
            "DOCS_ROUTE_ALIAS",
        )

        seen_routes = set()
        for route in routes:
            route_signature = (
                route.get("path"),
                (route.get("method") or "*").lower(),
                (route.get("canonical") or route.get("path")),
            )
            if route_signature in seen_routes:
                errors.append(
                    {
                        "severity": "error",
                        "code": "ROUTE_CONFLICT",
                        "message": f"Duplicate route signature: {route_signature}",
                        "suggested_fix": "Deduplicate route registration or split by method/content-type.",
                    }
                )
            seen_routes.add(route_signature)

        _collect_diagnostic_checks(
            checks,
            "route_conflicts",
            "ok" if not any(item["code"] == "ROUTE_CONFLICT" for item in errors) else "fail",
            "checked route signatures",
            "DOCS_ROUTE_CONFLICTS",
        )
    except Exception:
        warnings.append(
            {
                "severity": "warning",
                "code": "APP_INSPECT_FAILED",
                "message": "Could not load app for contract checks.",
                "suggested_fix": "Ensure app entrypoint imports safely; run from project directory.",
            }
        )
        _collect_diagnostic_checks(checks, "routing", "warn", "app inspection failed", "DOCS_ROUTING")

    cli_path = project_root / "app" / "cli"
    if cli_path.exists():
        nested_ok = _has_nested_cli_options(cli_path)
        _collect_diagnostic_checks(
            checks,
            "cli_nested_options",
            "ok" if nested_ok else "warn",
            "nested CLI options parser detected" if nested_ok else "no nested option pattern detected",
            "DOCS_CLI_NESTED",
        )
        if not nested_ok:
            warnings.append(
                {
                    "severity": "warning",
                    "code": "CLI_NESTED_OPTIONS",
                    "message": "No nested CLI patterns in app/cli discovered.",
                    "suggested_fix": "Ensure nested group options are described using `@group` + `@group.argument`.",
                }
            )
    else:
        warnings.append(
            {
                "severity": "warning",
                "code": "MISSING_CLI_DIR",
                "message": "Directory `app/cli` is missing.",
                "suggested_fix": "Add CLI modules under app/cli if CLI workflows are used.",
            }
        )
        _collect_diagnostic_checks(checks, "cli_nested_options", "warn", "app/cli missing", "DOCS_CLI_NESTED")

    models_dir = project_root / "app"
    map_model_ok = _has_map_model_autoincrement(models_dir)
    if map_model_ok:
        _collect_diagnostic_checks(
            checks,
            "map_model_autoincrement",
            "ok",
            "map_model with autoincrement confirmed",
            "DOCS_MAP_MODEL",
        )
    elif any("map_model(" in path.read_text(encoding="utf-8") for path in models_dir.glob("**/*.py")):
            warnings.append(
                {
                    "severity": "warning",
                    "code": "MAP_MODEL_AUTOINCREMENT",
                    "message": "map_model usage found, but autoincrement for int PK not guaranteed.",
                    "suggested_fix": "Set integer PK column with autoincrement for write models.",
                }
            )
            _collect_diagnostic_checks(
                checks,
                "map_model_autoincrement",
                "warn",
                "map_model usage found, but autoincrement for int PK not guaranteed",
                "DOCS_MAP_MODEL",
            )
    else:
        _collect_diagnostic_checks(
            checks,
            "map_model_autoincrement",
            "warn",
            "no map_model() usage with Integer autoincrement detected",
            "DOCS_MAP_MODEL",
        )

    otel_ok = _has_otel_hooks(project_root)
    _collect_diagnostic_checks(
        checks,
        "otel",
        "ok" if otel_ok else "warn",
        "otel hook pattern detected" if otel_ok else "no otel/watchdog hooks detected",
        "DOCS_OTEL",
    )
    if not otel_ok:
        warnings.append(
            {
                "severity": "warning",
                "code": "OTEL_HOOKS",
                "message": "OTel/watchdog hooks not confirmed.",
                "suggested_fix": "Add OTel bootstrap module and hook into app lifecycle.",
            }
        )

    return {
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
        "info": info,
    }


def run_project_tests(project_root: Path, timeout: float | int | None = None) -> int:
    env = os.environ.copy()
    env["PYTHONPATH"] = "." + (os.pathsep + env["PYTHONPATH"] if "PYTHONPATH" in env else "")
    try:
        process = subprocess.run(
            ["python", "-m", "pytest", "-q"],
            cwd=str(project_root),
            env=env,
            check=False,
            timeout=timeout if timeout and timeout > 0 else None,
        )
        return process.returncode
    except subprocess.TimeoutExpired:
        return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="muscles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Muscles project utility CLI",
        epilog=(
            "AI/CLI Cheat Sheet:\n"
            f"{AI_DSL_CHEAT_SHEET}\n"
            "Examples:\n"
            "  muscles create/project scaffolding:: muscles new demo --runtime asgi\n"
            "  muscles inspect contract::    muscles inspect --json --app app.application:App\n"
            "  muscles doctor checks::       muscles doctor --json\n"
        ),
    )

    def _add_global_options(target_parser: argparse.ArgumentParser) -> None:
        target_parser.add_argument("--json", action="store_true", help="JSON output when supported")
        target_parser.add_argument("--machine", action="store_true", help="Machine-readable mode (stdout JSON only)")
        target_parser.add_argument("--quiet", action="store_true", help="Quiet mode")
        target_parser.add_argument("--no-ansi", action="store_true", help="Disable ANSI colors/banners")
        target_parser.add_argument("--timeout", type=int, default=0, help="Timeout seconds for project commands (test/bootstrap)")

    _add_global_options(parser)
    subparsers = parser.add_subparsers(dest="command")

    new_parser = subparsers.add_parser("new", help="Create a new Muscles project")
    new_parser.add_argument("project_name")
    new_parser.add_argument("--runtime", default="asgi", choices=["asgi", "wsgi", "cli", "full"])
    new_parser.add_argument("--force", action="store_true")

    capabilities_parser = subparsers.add_parser("capabilities", help="Show CLI and project capabilities")

    generate_parser = subparsers.add_parser("generate", help="Generate Muscles artifacts")
    generate_parser.add_argument("generator_type", choices=["page", "api-resource", "cli-command", "value-object", "resource"])
    generate_parser.add_argument("name")
    generate_parser.add_argument("--force", action="store_true")
    generate_parser.add_argument("--with-tests", action="store_true")

    doctor_parser = subparsers.add_parser("doctor", help="Diagnose Muscles project")

    test_parser = subparsers.add_parser("test", help="Run canonical Muscles project tests")
    test_parser.add_argument("--doctor", action="store_true", help="Run doctor before tests")

    inspect_parser = subparsers.add_parser("inspect", help="Inspect Muscles application contract")
    inspect_parser.add_argument("--app", required=False, help="Entrypoint in module:ClassOrObject format")

    for command_name in ("actions", "routes", "schemas", "rules", "cli", "sql"):
        command_parser = subparsers.add_parser(command_name, help=f"Inspect {command_name}")
        command_parser.add_argument("--app", required=False, help="Entrypoint in module:ClassOrObject format")
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
    payload = inspect_application(app=app)
    payload.setdefault("performance_contract", {})
    payload["performance_contract"]["di_signature_cached"] = True
    return payload


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
        "performance_contract": {"di_signature_cached": True},
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
    global_parser = argparse.ArgumentParser(add_help=False)

    def _add_global_options(target_parser: argparse.ArgumentParser) -> None:
        target_parser.add_argument("--json", action="store_true", help="JSON output when supported")
        target_parser.add_argument("--machine", action="store_true", help="Machine-readable mode (stdout JSON only)")
        target_parser.add_argument("--quiet", action="store_true", help="Quiet mode")
        target_parser.add_argument("--no-ansi", action="store_true", help="Disable ANSI colors/banners")
        target_parser.add_argument("--timeout", type=int, default=0, help="Timeout seconds for project commands (test/bootstrap)")

    _add_global_options(global_parser)
    args_global, remaining_argv = global_parser.parse_known_args(argv)
    args = parser.parse_args(remaining_argv)
    for field in ("json", "machine", "quiet", "no_ansi", "timeout"):
        setattr(args, field, getattr(args_global, field))
    machine_mode = getattr(args, "machine", False)
    quiet_mode = getattr(args, "quiet", False)
    no_ansi = getattr(args, "no_ansi", False)
    timeout = getattr(args, "timeout", 0)
    suppress_ansi = machine_mode or no_ansi or not sys.stdout.isatty()

    def _render_text(value: object) -> str:
        payload = str(value)
        if suppress_ansi:
            return _ANSI_ESCAPE.sub("", payload)
        return payload

    def _emit(data, as_json: bool = False, *, stderr: bool = False):
        stream = sys.stderr if stderr else sys.stdout
        if machine_mode or as_json:
            stream.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        elif not quiet_mode:
            stream.write(_render_text(f"{data}\n"))

    try:
        if args.command == "capabilities":
            payload = build_capabilities_payload()
            as_json = getattr(args, "json", False) or machine_mode
            if as_json:
                _emit(payload, as_json=True)
                return EXIT_SUCCESS
            _emit("Muscles capabilities")
            _emit(f"runtime_mode: {payload['runtime_mode']}")
            _emit("commands:")
            for item in payload["commands"]:
                _emit(f" - {item['name']}: {item['syntax']}")
            return EXIT_SUCCESS

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

            if getattr(args, "json", False) or machine_mode:
                _emit(data, as_json=True)
            else:
                _emit(data)
            return EXIT_SUCCESS

        if args.command == "generate":
            generated = generate_artifact(
                project_root=Path.cwd(),
                generator_type=args.generator_type,
                name=args.name,
                force=args.force,
                with_tests=args.with_tests,
            )
            if machine_mode:
                _emit({"status": "ok", "generated": generated}, as_json=True)
                return EXIT_SUCCESS
            _emit("Generated files:")
            for item in generated:
                _emit(f" - {item}")
            _emit("Next steps:")
            _emit("  muscles inspect --json")
            _emit("  muscles test")
            return EXIT_SUCCESS

        if args.command == "doctor":
            root = detect_project_root()
            report = run_doctor(root)
            if getattr(args, "json", False) or machine_mode:
                _emit(report, as_json=True)
            else:
                _emit(report)
            return EXIT_SUCCESS if len(report["errors"]) == 0 else EXIT_INVALID_ARGUMENT

        if args.command == "test":
            root = detect_project_root()
            if getattr(args, "doctor", False):
                report = run_doctor(root)
                if len(report["errors"]) > 0:
                    if machine_mode:
                        _emit({"status": "error", "report": report}, as_json=True, stderr=True)
                    else:
                        _emit("Doctor failed. Fix errors before test run.")
                        _emit(report, as_json=True)
                    return EXIT_INVALID_ARGUMENT
            return run_project_tests(root, timeout=timeout)

        if args.command != "new":
            help_payload = {
                "framework": "Muscles",
                "commands": ["new", "capabilities"],
                "status": "ok",
            }
            if getattr(args, "json", False) or machine_mode:
                _emit(help_payload, as_json=True)
                return EXIT_SUCCESS
            parser.print_help()
            return EXIT_INVALID_ARGUMENT

        target = Path.cwd() / args.project_name
        files = scaffold_project(target=target, runtime=args.runtime, force=args.force)
        if machine_mode:
            _emit({"status": "ok", "target": str(target), "generated": files}, as_json=True)
            return EXIT_SUCCESS
        _emit(f"Created project at: {target}")
        _emit("Generated files:")
        for file_name in files:
            _emit(f" - {file_name}")
        _emit("Next steps:")
        _emit(f"  cd {args.project_name}")
        _emit("  PYTHONPATH=. python -m pytest -q")
        return EXIT_SUCCESS
    except Exception as exc:
        if machine_mode or getattr(args, "json", False):
            _emit(
                {
                    "status": "error",
                    "error": {
                        "type": exc.__class__.__name__,
                        "message": str(exc),
                    },
                },
                as_json=True,
                stderr=True,
            )
            return EXIT_INVALID_ARGUMENT
        return EXIT_RUNTIME_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
