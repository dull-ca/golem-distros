import json
import os
import subprocess
from pathlib import Path

from golem_distros import distros
from golem_distros.cli.booting import SEED_SCRIPT, seed_command
from golem_distros.cli.workspace import Workspace
from tests.doubles import stub_binaries

USER_DATA = "#cloud-config\nssh_authorized_keys:\n  - ssh-ed25519 AAAA test\n"


def run_seed(tmp_path: Path, name: str) -> subprocess.CompletedProcess:
    (tmp_path / "user-data").write_text(USER_DATA)
    stubs = stub_binaries(tmp_path / "stubs", {"genisoimage": ""})
    return subprocess.run(
        seed_command(
            distros.find(name),
            Workspace(root=str(tmp_path), output=str(tmp_path / "output")),
            str(tmp_path / "user-data"),
        ),
        env={
            **os.environ,
            "PATH": f"{stubs}{os.pathsep}{os.environ['PATH']}",
            "COMMAND_LOG": str(tmp_path / "commands.log"),
        },
        capture_output=True,
        text=True,
    )


def seed_directory(tmp_path: Path, name: str) -> Path:
    return tmp_path / "output" / "seed" / name


def test_a_nocloud_seed_is_labelled_cidata_and_holds_user_data_and_meta_data(tmp_path):
    finished = run_seed(tmp_path, "golem-do")
    assert finished.returncode == 0, finished.stderr
    directory = seed_directory(tmp_path, "golem-do")
    assert (directory / "user-data").read_text() == USER_DATA
    meta_data = (directory / "meta-data").read_text()
    assert "instance-id: golem-do" in meta_data
    assert "local-hostname: golem-do" in meta_data
    logged = (tmp_path / "commands.log").read_text()
    assert "-volid cidata" in logged
    assert str(tmp_path / "output" / "golem-do-seed.iso") in logged


def test_a_config_drive_seed_is_labelled_config_two_and_uses_the_openstack_layout(
    tmp_path,
):
    finished = run_seed(tmp_path, "golem-ovh")
    assert finished.returncode == 0, finished.stderr
    latest = seed_directory(tmp_path, "golem-ovh") / "openstack" / "latest"
    assert (latest / "user_data").read_text() == USER_DATA
    document = json.loads((latest / "meta_data.json").read_text())
    assert document["hostname"] == "golem-ovh"
    assert document["name"] == "golem-ovh"
    assert document["uuid"]
    assert "-volid config-2" in (tmp_path / "commands.log").read_text()


def test_a_stale_seed_directory_does_not_survive(tmp_path):
    stale = seed_directory(tmp_path, "golem-do") / "meta_data.json"
    stale.parent.mkdir(parents=True)
    stale.write_text("{}")
    run_seed(tmp_path, "golem-do")
    assert not stale.exists()


def test_an_unknown_seed_kind_is_refused_before_anything_is_removed(tmp_path):
    directory = tmp_path / "seed"
    directory.mkdir()
    finished = subprocess.run(
        [SEED_SCRIPT, "floppy", "golem-do", "user-data", str(directory), "seed.iso"],
        capture_output=True,
        text=True,
    )
    assert finished.returncode != 0
    assert "floppy" in finished.stderr
    assert directory.exists()
