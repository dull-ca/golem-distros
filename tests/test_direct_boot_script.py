import os
import subprocess
from pathlib import Path

from golem_distros.cli.booting import DIRECT_BOOT_SCRIPT
from tests.doubles import stub_binaries

GRUB = """
menuentry 'Debian GNU/Linux' {
\tload_video
\tlinux\t/boot/vmlinuz-6.19.8+deb13-amd64 root=PARTUUID=6d59fa39 ro  quiet
\tinitrd\t/boot/initrd.img-6.19.8+deb13-amd64
}
menuentry 'Debian GNU/Linux, recovery' {
\tlinux\t/boot/vmlinuz-6.12.107+deb13-amd64 root=PARTUUID=6d59fa39 ro single
\tinitrd\t/boot/initrd.img-6.12.107+deb13-amd64
}
"""

BROKEN_GRUB = "menuentry 'broken' {\n}\n"
KERNEL_ONLY_GRUB = "\tlinux\t/boot/vmlinuz-1 root=/dev/sda1\n"


def run_direct_boot(tmp_path: Path, grub: str) -> subprocess.CompletedProcess:
    configuration = tmp_path / "grub.cfg"
    configuration.write_text(grub)
    stubs = stub_binaries(
        tmp_path / "stubs", {"virt-cat": f'cat "{configuration}"\n', "virt-copy-out": ""}
    )
    environment = {
        **os.environ,
        "PATH": f"{stubs}{os.pathsep}{os.environ['PATH']}",
        "COMMAND_LOG": str(tmp_path / "commands.log"),
    }
    return subprocess.run(
        [DIRECT_BOOT_SCRIPT, str(tmp_path / "image.qcow2"), str(tmp_path / "boot")],
        env=environment,
        capture_output=True,
        text=True,
    )


def test_the_first_menu_entry_names_the_kernel_and_its_initrd(tmp_path):
    finished = run_direct_boot(tmp_path, GRUB)
    assert finished.returncode == 0, finished.stderr
    kernel, initrd, _ = finished.stdout.splitlines()
    assert kernel == str(tmp_path / "boot" / "vmlinuz-6.19.8+deb13-amd64")
    assert initrd == str(tmp_path / "boot" / "initrd.img-6.19.8+deb13-amd64")


def test_a_later_menu_entry_does_not_win(tmp_path):
    assert "6.12.107" not in run_direct_boot(tmp_path, GRUB).stdout


def test_the_command_line_adds_a_serial_console_to_the_image_arguments(tmp_path):
    command_line = run_direct_boot(tmp_path, GRUB).stdout.splitlines()[2]
    assert command_line == "root=PARTUUID=6d59fa39 ro quiet console=ttyS0,115200"


def test_the_kernel_and_initrd_are_copied_out_of_the_image(tmp_path):
    run_direct_boot(tmp_path, GRUB)
    logged = (tmp_path / "commands.log").read_text()
    assert "/boot/vmlinuz-6.19.8+deb13-amd64" in logged
    assert "/boot/initrd.img-6.19.8+deb13-amd64" in logged


def test_a_configuration_with_no_entry_fails(tmp_path):
    finished = run_direct_boot(tmp_path, BROKEN_GRUB)
    assert finished.returncode != 0
    assert "grub.cfg" in finished.stderr


def test_a_kernel_with_no_initrd_fails(tmp_path):
    assert run_direct_boot(tmp_path, KERNEL_ONLY_GRUB).returncode != 0
