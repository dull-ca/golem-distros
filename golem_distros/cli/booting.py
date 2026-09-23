import os
from dataclasses import dataclass
from pathlib import Path

from golem_distros.cli.building import image_path
from golem_distros.cli.workspace import Workspace
from golem_distros.model import Distro
from golem_distros.ports import Files, Runner

SCRIPTS = Path(__file__).resolve().parent.parent.parent / "image"
SEED_SCRIPT = str(SCRIPTS / "seed.sh")
DIRECT_BOOT_SCRIPT = str(SCRIPTS / "direct_boot.sh")
SEED_DIRECTORY = "seed"
KVM_DEVICE = "/dev/kvm"


@dataclass(frozen=True)
class DirectBoot:
    kernel: str
    initrd: str
    command_line: str


def seed_image_for(workspace: Workspace, distro: Distro) -> str:
    return f"{workspace.output}/{distro.name}-seed.iso"


def boot_directory_for(workspace: Workspace, distro: Distro) -> str:
    return f"{workspace.output}/{distro.name}-boot"


def seed_command(distro: Distro, workspace: Workspace, user_data: str) -> tuple[str, ...]:
    return (
        SEED_SCRIPT,
        distro.seed.value,
        distro.name,
        user_data,
        f"{workspace.output}/{SEED_DIRECTORY}/{distro.name}",
        seed_image_for(workspace, distro),
    )


def boot_command(
    image: str,
    memory: int,
    seed: str | None,
    accelerated: bool,
    direct: "DirectBoot | None" = None,
) -> tuple[str, ...]:
    argv: tuple[str, ...] = ("qemu-system-x86_64", "-m", str(memory))
    if accelerated:
        argv += ("-enable-kvm", "-cpu", "host")
    argv += ("-drive", f"file={image},format=qcow2,snapshot=on")
    if seed is not None:
        argv += ("-drive", f"file={seed},format=raw,media=cdrom,readonly=on")
    if direct is not None:
        argv += ("-kernel", direct.kernel, "-initrd", direct.initrd)
        argv += ("-append", direct.command_line)
    return argv + ("-nographic",)


def prepare_direct_boot(distro: Distro, workspace: Workspace, runner: Runner) -> DirectBoot:
    kernel, initrd, command_line = runner.capture(
        (DIRECT_BOOT_SCRIPT, image_path(workspace, distro), boot_directory_for(workspace, distro))
    ).splitlines()
    return DirectBoot(kernel=kernel, initrd=initrd, command_line=command_line)


def kvm_is_available() -> bool:
    device = Path(KVM_DEVICE)
    return device.exists() and os.access(device, os.R_OK | os.W_OK)


def boot_image(
    distro: Distro,
    workspace: Workspace,
    seed_file: str | None,
    memory: int,
    runner: Runner,
    files: Files,
    directly: bool = False,
) -> None:
    image = image_path(workspace, distro)
    if not files.exists(image):
        raise FileNotFoundError(f"no image at {image}; build {distro.name} first")
    seed = None
    if seed_file is not None:
        seed = seed_image_for(workspace, distro)
        runner.run(seed_command(distro, workspace, seed_file))
    prepared = prepare_direct_boot(distro, workspace, runner) if directly else None
    runner.run(boot_command(image, memory, seed, kvm_is_available(), prepared))
