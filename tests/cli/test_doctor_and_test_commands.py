from pathlib import Path

from muscles.cli.tooling import run_doctor
from muscles.cli.tooling import run_project_tests
from muscles.cli.tooling import scaffold_project


def test_doctor_passes_on_scaffold_project(tmp_path):
    project = tmp_path / "demo"
    scaffold_project(target=project, runtime="asgi", force=False)
    report = run_doctor(project)
    assert report["errors"] == []


def test_doctor_detects_missing_tests(tmp_path):
    project = tmp_path / "demo"
    scaffold_project(target=project, runtime="asgi", force=False)
    for test_file in (project / "tests").glob("test_*.py"):
        test_file.unlink()
    report = run_doctor(project)
    assert any(item["code"] == "MISSING_TESTS" for item in report["errors"])


def test_run_project_tests_returns_success_for_scaffold(tmp_path):
    project = tmp_path / "demo"
    scaffold_project(target=project, runtime="asgi", force=False)
    code = run_project_tests(project)
    assert code == 0
