import pytest

from muscles.cli.tooling import generate_artifact
from muscles.cli.tooling import scaffold_project


def test_generate_page_creates_code_and_test(tmp_path):
    project = tmp_path / "demo"
    scaffold_project(target=project, runtime="asgi", force=False)

    generated = generate_artifact(project_root=project, generator_type="page", name="Home", force=False, with_tests=True)
    assert "app/web/home.py" in generated
    assert "tests/test_page_home.py" in generated


def test_generate_value_object_creates_domain_file(tmp_path):
    project = tmp_path / "demo"
    scaffold_project(target=project, runtime="asgi", force=False)

    generated = generate_artifact(project_root=project, generator_type="value-object", name="EmailAddress", force=False, with_tests=False)
    assert "app/domain/emailaddress.py" in generated


def test_generate_resource_creates_schema_api_cli_and_tests(tmp_path):
    project = tmp_path / "demo"
    scaffold_project(target=project, runtime="asgi", force=False)

    generated = generate_artifact(project_root=project, generator_type="resource", name="Booking", force=False, with_tests=True)
    assert "app/schemas/booking.py" in generated
    assert "app/api/booking.py" in generated
    assert "app/cli/booking.py" in generated
    assert "tests/test_resource_booking.py" in generated


def test_generate_prevents_overwrite_without_force(tmp_path):
    project = tmp_path / "demo"
    scaffold_project(target=project, runtime="asgi", force=False)
    generate_artifact(project_root=project, generator_type="page", name="Home", force=False, with_tests=False)

    with pytest.raises(FileExistsError):
        generate_artifact(project_root=project, generator_type="page", name="Home", force=False, with_tests=False)
