import hashlib
import os
import subprocess
from pathlib import Path

import pytest

from golem_distros import distros
from golem_distros.cli.building import BUILD_SCRIPT, build_command, build_image
from golem_distros.cli.workspace import Workspace
from tests.doubles import WORKSPACE, FakeFiles, RecordingRunner, stub_binaries

BASE_CONTENT = b"a pinned base image"
BASE_DIGEST = hashlib.sha512(BASE_CONTENT).hexdigest()
WRONG_DIGEST = "d" * 128
IMAGE_DIGEST = "c" * 128
LOG = "commands.log"
GOLEMD = "/nix/store/abc/bin/golemd"
REPOSITORY = str(Path(BUILD_SCRIPT).resolve().parent.parent)

TOUCH_OUTPUTS = (
    'for argument in "$@"; do\n'
    '    case "$argument" in "$STUB_OUTPUT"/*) [ -e "$argument" ] || : > "$argument" ;; esac\n'
    "done\n"
)

STUBS = {
    "curl": (
        'while [ "$#" -gt 0 ]; do\n'
        '    if [ "$1" = "-o" ]; then printf "the downloaded base" > "$2"; fi\n'
        "    shift\n"
        "done\n"
    ),
    "qemu-img": TOUCH_OUTPUTS,
    "virt-resize": TOUCH_OUTPUTS,
    "virt-customize": "",
}


def run_build(tmp_path: Path, digest: str) -> subprocess.CompletedProcess:
    workspace = Workspace(root=str(tmp_path), output=str(tmp_path / "output"))
    distro = distros.find("golem-do")
    command = list(build_command(distro, workspace, GOLEMD))
    command[command.index(distro.base.sha512)] = digest
    environment = {
        **os.environ,
        "PATH": f"{stub_binaries(tmp_path / 'stubs', STUBS)}{os.pathsep}{os.environ['PATH']}",
        "COMMAND_LOG": str(tmp_path / LOG),
        "STUB_OUTPUT": str(tmp_path / "output"),
    }
    return subprocess.run(command, env=environment, capture_output=True, text=True)


def with_cached_base(tmp_path: Path) -> None:
    output = tmp_path / "output"
    output.mkdir()
    (output / distros.find("golem-do").base.filename).write_bytes(BASE_CONTENT)


def logged(tmp_path: Path) -> list[str]:
    log = tmp_path / LOG
    if not log.exists():
        return []
    return [line.split()[0] for line in log.read_text().splitlines()]


def preview(tmp_path: Path, name: str) -> str:
    workspace = Workspace(root=str(tmp_path), output=str(tmp_path / "output"))
    command = build_command(distros.find(name), workspace, GOLEMD, dry_run=True)
    finished = subprocess.run(list(command), capture_output=True, text=True)
    assert finished.returncode == 0, finished.stderr
    return finished.stdout


def test_a_mismatched_base_names_the_pin_and_runs_no_qemu_img_or_virt_customize(
    tmp_path,
):
    with_cached_base(tmp_path)
    finished = run_build(tmp_path, WRONG_DIGEST)
    assert finished.returncode != 0
    assert WRONG_DIGEST in finished.stderr
    assert logged(tmp_path) == []


def test_a_downloaded_base_is_verified_before_any_qemu_img(tmp_path):
    finished = run_build(tmp_path, BASE_DIGEST)
    assert finished.returncode != 0
    assert logged(tmp_path) == ["curl"]


def test_a_matching_base_builds_in_order_and_leaves_the_image_read_only(tmp_path):
    with_cached_base(tmp_path)
    finished = run_build(tmp_path, BASE_DIGEST)
    assert finished.returncode == 0, finished.stderr
    assert logged(tmp_path) == ["qemu-img", "virt-resize", "virt-customize", "qemu-img"]
    image = tmp_path / "output" / "golem-do.qcow2"
    assert image.stat().st_mode & 0o777 == 0o444


def test_a_dry_run_runs_nothing_and_creates_no_output_directory(tmp_path):
    printed = preview(tmp_path, "golem-do")
    assert "qemu-img create" in printed
    assert "virt-customize" in printed
    assert not (tmp_path / "output").exists()


def test_the_command_carries_the_pinned_base_and_the_disk_layout():
    distro = distros.find("golem-do")
    assert build_command(distro, WORKSPACE, GOLEMD)[:7] == (
        BUILD_SCRIPT,
        "golem-do",
        distro.base.url,
        distro.base.sha512,
        "8G",
        "/dev/sda1",
        WORKSPACE.output,
    )


def customization(tmp_path: Path, name: str) -> str:
    return next(
        line
        for line in preview(tmp_path, name).splitlines()
        if line.startswith("virt-customize")
    )


@pytest.mark.parametrize("distro", distros.all_distros(), ids=distros.names())
def test_every_declared_step_runs_in_order(tmp_path, distro):
    words = customization(tmp_path, distro.name).split()
    runs = [
        word.removeprefix(f"{REPOSITORY}/")
        for index, word in enumerate(words)
        if index and words[index - 1] == "--run"
    ]
    assert runs == [step.script for step in distro.steps]


def test_a_payload_is_copied_in_immediately_before_the_step_that_needs_it(tmp_path):
    assert (
        f"--mkdir /tmp --copy-in {GOLEMD}:/tmp --chown 0:0:/tmp/golemd "
        f"--run {REPOSITORY}/provision/20-golemd.sh"
    ) in customization(tmp_path, "golem-ovh")


def test_the_ovh_boot_hook_is_copied_in_last_owned_by_root_at_mode_0700(tmp_path):
    hook = f"{REPOSITORY}/files/ovh/make_image_bootable.sh"
    assert customization(tmp_path, "golem-ovh").endswith(
        f"--mkdir /root/.ovh --copy-in {hook}:/root/.ovh "
        "--chown 0:0:/root/.ovh/make_image_bootable.sh "
        "--chmod 0700:/root/.ovh/make_image_bootable.sh"
    )


def test_an_unknown_action_is_refused(tmp_path):
    workspace = Workspace(root=str(tmp_path), output=str(tmp_path / "output"))
    command = list(build_command(distros.find("golem-do"), workspace, GOLEMD))
    finished = subprocess.run(
        command[: command.index("run")] + ["dance"], capture_output=True, text=True
    )
    assert finished.returncode != 0
    assert "dance" in finished.stderr


def test_the_build_runs_one_command_and_reports_the_image_digest():
    runner = RecordingRunner()
    image = f"{WORKSPACE.output}/golem-do.qcow2"
    built = build_image(
        distros.find("golem-do"),
        WORKSPACE,
        GOLEMD,
        runner,
        FakeFiles(digests={image: IMAGE_DIGEST}),
    )
    assert runner.calls == [build_command(distros.find("golem-do"), WORKSPACE, GOLEMD)]
    assert (built.distro_name, built.path, built.sha512) == (
        "golem-do",
        image,
        IMAGE_DIGEST,
    )
