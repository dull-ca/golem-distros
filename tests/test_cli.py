from pathlib import Path

import pytest
from typer.testing import CliRunner

from golem_distros.cli import main
from golem_distros.cli.main import app
from golem_distros.cli.workspace import Workspace
from tests.doubles import RecordingRunner

runner = CliRunner()

CREDENTIAL_VARIABLES = (
    "GOLEM_DISTROS_IMAGE_BUCKET",
    "GOLEM_DISTROS_IMAGE_REGION",
    "GOLEM_DISTROS_IMAGE_ENDPOINT",
    "GOLEM_DISTROS_IMAGE_BASE_URL",
    "GOLEM_DISTROS_IMAGE_PROVIDER",
    "GOLEM_DISTROS_IMAGE_ACL",
    "GOLEM_DISTROS_IMAGES_ACCESS_KEY_ID",
    "GOLEM_DISTROS_IMAGES_SECRET_ACCESS_KEY",
)


@pytest.fixture
def workspace(monkeypatch, tmp_path: Path) -> Path:
    isolated = Workspace(root=str(tmp_path), output=str(tmp_path / "output"))
    monkeypatch.setattr(Workspace, "discover", classmethod(lambda cls: isolated))
    return tmp_path


@pytest.fixture
def without_credentials(monkeypatch) -> None:
    for name in CREDENTIAL_VARIABLES:
        monkeypatch.delenv(name, raising=False)


def a_built_image(workspace: Path) -> None:
    (workspace / "output").mkdir()
    (workspace / "output" / "golem-do.qcow2").write_bytes(b"fake-image")


def test_list_prints_every_configuration():
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "golem-ovh" in result.stdout
    assert "golem-do" in result.stdout


def test_build_rejects_an_unknown_configuration():
    result = runner.invoke(app, ["build", "golem-nothing"])
    assert result.exit_code != 0
    assert "golem-nothing" in result.stdout


def test_a_dry_run_build_prints_the_commands_and_creates_nothing(workspace):
    result = runner.invoke(app, ["build", "golem-do", "--dry-run"])
    assert result.exit_code == 0
    assert "curl" in result.stdout
    assert "qemu-img create" in result.stdout
    assert "virt-customize" in result.stdout
    assert not (workspace / "output").exists()


def test_publish_reports_a_missing_credential_cleanly(workspace, without_credentials):
    a_built_image(workspace)
    result = runner.invoke(app, ["publish", "golem-do", "--version", "v1.0.0"])
    assert result.exit_code == 2
    assert isinstance(result.exception, SystemExit)
    assert "publishing needs" in result.stdout


def test_a_dry_run_publish_succeeds_with_no_credentials(workspace, without_credentials):
    a_built_image(workspace)
    result = runner.invoke(
        app, ["publish", "golem-do", "--version", "v1.0.0", "--dry-run"]
    )
    assert result.exit_code == 0
    assert "publishing needs" not in result.stdout
    assert "rclone copyto" in result.stdout


def test_a_dry_run_publish_never_prints_a_real_secret(workspace, monkeypatch):
    monkeypatch.setenv("GOLEM_DISTROS_IMAGES_ACCESS_KEY_ID", "real-access-key")
    monkeypatch.setenv("GOLEM_DISTROS_IMAGES_SECRET_ACCESS_KEY", "real-secret-key")
    a_built_image(workspace)
    result = runner.invoke(
        app, ["publish", "golem-do", "--version", "v1.0.0", "--dry-run"]
    )
    assert result.exit_code == 0
    assert "real-access-key" not in result.stdout
    assert "real-secret-key" not in result.stdout


def test_publish_refuses_when_the_image_was_never_built(workspace, without_credentials):
    result = runner.invoke(app, ["publish", "golem-do", "--version", "v1.0.0"])
    assert result.exit_code == 2
    assert "build golem-do first" in result.stdout


def test_release_reports_a_missing_credential_cleanly(
    workspace, without_credentials, monkeypatch
):
    monkeypatch.setattr(main, "Subprocess", lambda: RecordingRunner())
    result = runner.invoke(app, ["release"])
    assert result.exit_code == 2
    assert isinstance(result.exception, SystemExit)
    assert "publishing needs" in result.stdout
