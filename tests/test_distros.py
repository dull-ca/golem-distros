from pathlib import Path

import pytest

from golem_distros import bases, distros
from golem_distros.model import GOLEMD_SOURCE, SeedKind

ROOT = Path(__file__).resolve().parent.parent
FORBIDDEN = (
    "authorized_keys",
    "ssh-ed25519",
    "ssh-rsa",
    "users_groups",
    "users-groups",
    "set_passwords",
    "set-passwords",
)


def test_the_registry_is_sorted_keyed_by_name_and_refuses_an_unknown_name():
    assert distros.names() == sorted(distros.names())
    for key, distro in distros.REGISTRY.items():
        assert key == distro.name
    with pytest.raises(distros.UnknownDistro):
        distros.find("golem-nothing")


def test_every_step_script_exists_and_is_executable():
    for distro in distros.REGISTRY.values():
        for step in distro.steps:
            script = ROOT / step.script
            assert script.is_file()
            assert script.stat().st_mode & 0o111


def test_every_payload_source_exists_or_is_the_golemd_sentinel():
    for distro in distros.REGISTRY.values():
        sources = [payload.source for payload in distro.payloads]
        for step in distro.steps:
            sources.extend(payload.source for payload in step.payloads)
        for source in sources:
            assert source == GOLEMD_SOURCE or (ROOT / source).is_file()


def test_each_configuration_asks_for_the_seed_its_platform_reads():
    assert distros.find("golem-ovh").seed is SeedKind.CONFIG_DRIVE
    assert distros.find("golem-do").seed is SeedKind.NOCLOUD


def test_ovh_installs_the_boot_hook_with_mode_0700():
    payloads = distros.find("golem-ovh").payloads
    assert [payload.destination for payload in payloads] == ["/root/.ovh"]
    assert payloads[0].mode == "0700"


def test_every_configuration_uses_the_same_pinned_dated_base():
    for distro in distros.REGISTRY.values():
        assert distro.base is bases.DEBIAN_TRIXIE
    assert "/latest/" not in bases.DEBIAN_TRIXIE.url
    assert len(bases.DEBIAN_TRIXIE.sha512) == 128


def test_no_script_bakes_an_ssh_key_or_drops_the_cloud_init_user_modules():
    paths = [
        path
        for directory in (ROOT / "provision", ROOT / "files", ROOT / "image")
        for path in directory.rglob("*")
        if path.is_file()
    ]
    assert paths
    for path in paths:
        text = path.read_text()
        for forbidden in FORBIDDEN:
            assert forbidden not in text, f"{path} names {forbidden}"
