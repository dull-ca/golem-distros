import json

from golem_distros.manifest import (
    PublishedGolemd,
    PublishedImage,
    PublishedRelease,
    published_manifest_json,
)
from golem_distros.model import BaseImage

RELEASE = PublishedRelease(
    version="v1.4.0",
    released="2026-09-12T20:31:04Z",
    commit="8f2c1ab",
    golemd=PublishedGolemd(flake="github:dull-ca/golem", rev="41bf030"),
    images={
        "golem-ovh": PublishedImage(
            url="https://host/golem-ovh/v1.4.0/golem-ovh-a1b2.qcow2",
            sha512="a" * 128,
            checksum_url="https://host/golem-ovh/v1.4.0/golem-ovh-a1b2.qcow2.sha512",
            base=BaseImage(
                url="https://cloud.debian.org/base.qcow2", sha512="b" * 128
            ),
        )
    },
)


def test_the_manifest_ends_with_a_newline():
    assert published_manifest_json(RELEASE).endswith("\n")


def test_the_manifest_records_the_version_the_commit_and_the_time():
    document = json.loads(published_manifest_json(RELEASE))
    assert document["version"] == "v1.4.0"
    assert document["commit"] == "8f2c1ab"
    assert document["released"] == "2026-09-12T20:31:04Z"


def test_the_manifest_records_the_golemd_input():
    assert json.loads(published_manifest_json(RELEASE))["golemd"] == {
        "flake": "github:dull-ca/golem",
        "rev": "41bf030",
    }


def test_the_manifest_records_each_image_with_its_checksum_and_its_base():
    assert json.loads(published_manifest_json(RELEASE))["images"]["golem-ovh"] == {
        "url": "https://host/golem-ovh/v1.4.0/golem-ovh-a1b2.qcow2",
        "sha512": "a" * 128,
        "checksum_url": "https://host/golem-ovh/v1.4.0/golem-ovh-a1b2.qcow2.sha512",
        "base": {"url": "https://cloud.debian.org/base.qcow2", "sha512": "b" * 128},
    }
