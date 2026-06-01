from __future__ import annotations

from pathlib import Path

from muscles.core import GenerationRequest, GeneratorRegistry


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _safe_write_file(path: Path, content: str, force: bool) -> str:
    if path.exists() and not force:
        raise FileExistsError(f"File `{path}` already exists. Use --force to overwrite.")
    _write(path, content)
    return str(path)


class CliCommandGeneratorProvider:
    name = "cli-command"

    def supports(self, generator_type: str) -> bool:
        return generator_type == "cli-command"

    def generate(self, project_root: Path, request: GenerationRequest) -> list[str]:
        app_dir = project_root / "app"
        slug = request.name.replace(".", "_").replace("-", "_").lower()
        generated = [
            str(
                Path(
                    _safe_write_file(
                        app_dir / "cli" / f"{slug}.py",
                        f"def {slug}(*args, **kwargs):\n    return True\n",
                        request.force,
                    )
                ).relative_to(project_root)
            )
        ]
        if request.with_tests:
            generated.append(
                str(
                    Path(
                        _safe_write_file(
                            project_root / "tests" / f"test_cli_{slug}.py",
                            f"def test_cli_{slug}():\n    assert True\n",
                            request.force,
                        )
                    ).relative_to(project_root)
                )
            )
        return generated


class CoreGeneratorProvider:
    name = "core"

    def supports(self, generator_type: str) -> bool:
        return generator_type in {"page", "api-resource", "value-object", "resource"}

    def generate(self, project_root: Path, request: GenerationRequest) -> list[str]:
        app_dir = project_root / "app"
        slug = request.name.replace(".", "_").replace("-", "_").lower()
        generated: list[str] = []
        generator_type = request.generator_type

        if generator_type == "page":
            generated.append(
                str(
                    Path(
                        _safe_write_file(
                            app_dir / "web" / f"{slug}.py",
                            f"def {slug}(*args, **kwargs):\n    return '{request.name}'\n",
                            request.force,
                        )
                    ).relative_to(project_root)
                )
            )
            if request.with_tests:
                generated.append(
                    str(
                        Path(
                            _safe_write_file(
                                project_root / "tests" / f"test_page_{slug}.py",
                                f"def test_page_{slug}():\n    assert True\n",
                                request.force,
                            )
                        ).relative_to(project_root)
                    )
                )
            return generated

        if generator_type == "api-resource":
            generated.append(
                str(
                    Path(
                        _safe_write_file(
                            app_dir / "api" / f"{slug}.py",
                            f"def create_{slug}(*args, **kwargs):\n    return {{'resource': '{request.name}'}}\n",
                            request.force,
                        )
                    ).relative_to(project_root)
                )
            )
            generated.append(
                str(
                    Path(
                        _safe_write_file(
                            app_dir / "schemas" / f"{slug}.py",
                            f"class {request.name}Schema:\n    pass\n",
                            request.force,
                        )
                    ).relative_to(project_root)
                )
            )
            if request.with_tests:
                generated.append(
                    str(
                        Path(
                            _safe_write_file(
                                project_root / "tests" / f"test_api_{slug}.py",
                                f"def test_api_{slug}():\n    assert True\n",
                                request.force,
                            )
                        ).relative_to(project_root)
                    )
                )
            return generated

        if generator_type == "value-object":
            generated.append(
                str(
                    Path(
                        _safe_write_file(
                            app_dir / "domain" / f"{slug}.py",
                            f"class {request.name}:\n    pass\n",
                            request.force,
                        )
                    ).relative_to(project_root)
                )
            )
            if request.with_tests:
                generated.append(
                    str(
                        Path(
                            _safe_write_file(
                                project_root / "tests" / f"test_value_object_{slug}.py",
                                f"def test_value_object_{slug}():\n    assert True\n",
                                request.force,
                            )
                        ).relative_to(project_root)
                    )
                )
            return generated

        if generator_type == "resource":
            registry = default_generator_registry()
            generated.extend(
                registry.resolve("api-resource").generate(
                    project_root,
                    GenerationRequest(generator_type="api-resource", name=request.name, force=request.force, with_tests=False),
                )
            )
            generated.extend(
                registry.resolve("cli-command").generate(
                    project_root,
                    GenerationRequest(generator_type="cli-command", name=request.name, force=request.force, with_tests=False),
                )
            )
            if request.with_tests:
                generated.append(
                    str(
                        Path(
                            _safe_write_file(
                                project_root / "tests" / f"test_resource_{slug}.py",
                                f"def test_resource_{slug}():\n    assert True\n",
                                request.force,
                            )
                        ).relative_to(project_root)
                    )
                )
            return generated

        raise ValueError(f"Unsupported generator type `{generator_type}`")


_DEFAULT_REGISTRY: GeneratorRegistry | None = None


def default_generator_registry() -> GeneratorRegistry:
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        registry = GeneratorRegistry()
        registry.register(CoreGeneratorProvider())
        registry.register(CliCommandGeneratorProvider())
        _DEFAULT_REGISTRY = registry
    return _DEFAULT_REGISTRY

