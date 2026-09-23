import pytest

from golem_distros import distros
from golem_distros.cli.booting import (
    DIRECT_BOOT_SCRIPT,
    SEED_SCRIPT,
    DirectBoot,
    boot_command,
    boot_image,
    prepare_direct_boot,
    seed_image_for,
)
from tests.doubles import WORKSPACE, FakeFiles, RecordingRunner

IMAGE = "/repo/output/golem-do.qcow2"
OVH_IMAGE = "/repo/output/golem-ovh.qcow2"
SEED_TEXT_PATH = "/tmp/user-data"
PREPARED = (
    "/repo/output/golem-ovh-boot/vmlinuz-6.19.8\n"
    "/repo/output/golem-ovh-boot/initrd.img-6.19.8\n"
    "root=PARTUUID=abc ro quiet console=ttyS0,115200\n"
)


def test_the_boot_command_discards_writes():
    argv = boot_command(IMAGE, 4096, None, accelerated=False)
    assert argv == (
        "qemu-system-x86_64",
        "-m",
        "4096",
        "-drive",
        f"file={IMAGE},format=qcow2,snapshot=on",
        "-nographic",
    )


def test_acceleration_is_added_when_kvm_is_available():
    argv = boot_command(IMAGE, 2048, None, accelerated=True)
    assert "-enable-kvm" in argv
    assert ("-cpu", "host") in list(zip(argv, argv[1:]))


def test_a_seed_is_attached_as_a_read_only_cdrom():
    argv = boot_command(IMAGE, 2048, "/tmp/seed.iso", accelerated=False)
    assert "file=/tmp/seed.iso,format=raw,media=cdrom,readonly=on" in argv


def test_booting_without_a_seed_runs_exactly_one_command():
    runner = RecordingRunner()
    boot_image(distros.find("golem-do"), WORKSPACE, None, 2048, runner, FakeFiles([IMAGE]))
    assert len(runner.calls) == 1
    assert runner.calls[0][0] == "qemu-system-x86_64"


def test_booting_with_a_seed_builds_the_seed_then_attaches_it():
    runner = RecordingRunner()
    boot_image(
        distros.find("golem-do"), WORKSPACE, SEED_TEXT_PATH, 2048, runner, FakeFiles([IMAGE])
    )
    assert [call[0] for call in runner.calls] == [SEED_SCRIPT, "qemu-system-x86_64"]
    assert runner.calls[0][1:4] == ("nocloud", "golem-do", SEED_TEXT_PATH)
    seed = seed_image_for(WORKSPACE, distros.find("golem-do"))
    assert f"file={seed},format=raw,media=cdrom,readonly=on" in runner.calls[1]


def test_a_config_drive_configuration_asks_the_script_for_its_own_kind():
    runner = RecordingRunner()
    boot_image(
        distros.find("golem-ovh"), WORKSPACE, SEED_TEXT_PATH, 2048, runner, FakeFiles([OVH_IMAGE])
    )
    assert runner.calls[0][1:3] == ("config-drive", "golem-ovh")


def test_configurations_do_not_share_a_seed_image_path():
    assert seed_image_for(WORKSPACE, distros.find("golem-do")) != seed_image_for(
        WORKSPACE, distros.find("golem-ovh")
    )


def test_booting_a_missing_image_raises_with_the_path_in_the_message():
    with pytest.raises(FileNotFoundError, match=IMAGE):
        boot_image(distros.find("golem-do"), WORKSPACE, None, 2048, RecordingRunner(), FakeFiles())


def test_only_a_direct_boot_passes_a_kernel_an_initrd_and_a_command_line():
    command_line = "root=PARTUUID=abc ro quiet console=ttyS0,115200"
    direct = DirectBoot("/o/vmlinuz-6.19.8", "/o/initrd.img-6.19.8", command_line)
    argv = boot_command(OVH_IMAGE, 2048, None, accelerated=False, direct=direct)
    assert ("-kernel", direct.kernel) in list(zip(argv, argv[1:]))
    assert ("-initrd", direct.initrd) in list(zip(argv, argv[1:]))
    assert ("-append", command_line) in list(zip(argv, argv[1:]))
    plain = boot_command(IMAGE, 2048, None, accelerated=False, direct=None)
    assert "-kernel" not in plain
    assert "-append" not in plain


def test_preparing_a_direct_boot_reads_back_what_the_script_found():
    runner = RecordingRunner(outputs={DIRECT_BOOT_SCRIPT: PREPARED})
    prepared = prepare_direct_boot(distros.find("golem-ovh"), WORKSPACE, runner)
    assert runner.calls == [
        (DIRECT_BOOT_SCRIPT, OVH_IMAGE, "/repo/output/golem-ovh-boot")
    ]
    assert prepared.kernel == "/repo/output/golem-ovh-boot/vmlinuz-6.19.8"
    assert prepared.initrd == "/repo/output/golem-ovh-boot/initrd.img-6.19.8"
    assert prepared.command_line == "root=PARTUUID=abc ro quiet console=ttyS0,115200"
