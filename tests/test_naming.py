import pytest

from golem_distros import naming

DIGEST = "a1b2c3d4e5f60718" + "9" * 112
BASE_URL = "https://golem-distros.s3.gra.io.cloud.ovh.net"


def test_the_image_key_includes_the_configuration_the_version_and_the_hash():
    assert naming.image_key("golem-ovh", "v1.4.0", DIGEST) == (
        "golem-ovh/v1.4.0/golem-ovh-a1b2c3d4e5f60718.qcow2"
    )


def test_the_image_key_rejects_a_digest_of_the_wrong_length():
    with pytest.raises(ValueError):
        naming.image_key("golem-ovh", "v1.4.0", "abc")


def test_the_manifest_key_names_the_version():
    assert naming.manifest_key("v1.4.0") == "releases/v1.4.0.json"


def test_the_latest_key_is_fixed():
    assert naming.LATEST_KEY == "releases/latest.json"


def test_the_public_url_joins_with_exactly_one_slash():
    key = naming.image_key("golem-ovh", "v1.4.0", DIGEST)
    assert naming.public_url(BASE_URL + "/", key) == naming.public_url(BASE_URL, key)
    assert naming.public_url(BASE_URL, key) == (
        "https://golem-distros.s3.gra.io.cloud.ovh.net/"
        "golem-ovh/v1.4.0/golem-ovh-a1b2c3d4e5f60718.qcow2"
    )


def test_the_published_name_is_the_last_part_of_the_key():
    key = naming.image_key("golem-do", "v2.0.0", DIGEST)
    assert naming.published_name(key) == "golem-do-a1b2c3d4e5f60718.qcow2"


def test_the_sidecar_matches_the_sha512sum_check_format():
    assert naming.sidecar(DIGEST, "golem-do-a1b2.qcow2") == (
        f"{DIGEST}  golem-do-a1b2.qcow2\n"
    )
