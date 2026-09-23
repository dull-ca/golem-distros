import pytest

from golem_distros.cli.building import BuiltImage
from golem_distros.cli.publishing import (
    access_check_command,
    aws_environment,
    publish_image,
    publish_text,
    rclone_environment,
)
from tests.doubles import DESTINATION, WORKSPACE, FakeFiles, RecordingRunner

DIGEST = "a1b2c3d4e5f60718" + "9" * 112
BUILT = BuiltImage(
    distro_name="golem-do", path="/repo/output/golem-do.qcow2", sha512=DIGEST
)
IMAGE_KEY = "golem-do/v1.4.0/golem-do-a1b2c3d4e5f60718.qcow2"


def a_publish(runner: RecordingRunner, files: FakeFiles):
    return publish_image(BUILT, "v1.4.0", DESTINATION, WORKSPACE, runner, files)


def test_the_rclone_environment_uses_the_configured_provider_endpoint_and_acl():
    environment = rclone_environment(DESTINATION)
    assert environment["RCLONE_CONFIG_IMAGES_TYPE"] == "s3"
    assert environment["RCLONE_CONFIG_IMAGES_PROVIDER"] == "Other"
    assert environment["RCLONE_CONFIG_IMAGES_ENDPOINT"] == "s3.gra.io.cloud.ovh.net"
    assert environment["RCLONE_CONFIG_IMAGES_REGION"] == "gra"
    assert environment["RCLONE_CONFIG_IMAGES_ACL"] == "public-read"
    assert environment["RCLONE_CONFIG_IMAGES_ACCESS_KEY_ID"] == "key"
    assert environment["RCLONE_CONFIG_IMAGES_SECRET_ACCESS_KEY"] == "secret"


def test_publishing_copies_the_image_then_the_sidecar_to_exact_keys():
    runner = RecordingRunner()
    a_publish(runner, FakeFiles(present=[BUILT.path]))
    assert len(runner.calls) == 2
    assert runner.calls[0][:4] == (
        "rclone",
        "copyto",
        BUILT.path,
        f"images:golem-distros/{IMAGE_KEY}",
    )
    assert runner.calls[1][3] == f"images:golem-distros/{IMAGE_KEY}.sha512"


def test_publishing_sends_credentials_to_the_runner_on_both_uploads():
    runner = RecordingRunner()
    a_publish(runner, FakeFiles(present=[BUILT.path]))
    assert len(runner.environments) == 2
    for environment in runner.environments:
        assert environment["RCLONE_CONFIG_IMAGES_ACCESS_KEY_ID"] == "key"
        assert environment["RCLONE_CONFIG_IMAGES_SECRET_ACCESS_KEY"] == "secret"


def test_publishing_returns_the_public_urls():
    published = a_publish(RecordingRunner(), FakeFiles(present=[BUILT.path]))
    assert published.url == (
        "https://golem-distros.s3.gra.io.cloud.ovh.net/" + IMAGE_KEY
    )
    assert published.checksum_url == published.url + ".sha512"
    assert published.sha512 == DIGEST


def test_the_sidecar_names_the_published_object_not_the_local_file():
    files = FakeFiles(present=[BUILT.path])
    a_publish(RecordingRunner(), files)
    sidecar = files.written["/repo/output/golem-do-a1b2c3d4e5f60718.qcow2.sha512"]
    assert sidecar == f"{DIGEST}  golem-do-a1b2c3d4e5f60718.qcow2\n"


def test_publishing_refuses_when_the_image_is_missing():
    with pytest.raises(FileNotFoundError):
        a_publish(RecordingRunner(), FakeFiles())


def test_publish_text_writes_the_text_locally_then_uploads_it_to_the_exact_key():
    files, runner = FakeFiles(), RecordingRunner()
    url = publish_text(
        "{}", "releases/v1.0.0.json", DESTINATION, WORKSPACE, runner, files
    )
    assert files.written["/repo/output/v1.0.0.json"] == "{}"
    assert len(runner.calls) == 1
    assert runner.calls[0][:4] == (
        "rclone",
        "copyto",
        "/repo/output/v1.0.0.json",
        "images:golem-distros/releases/v1.0.0.json",
    )
    assert runner.environments[0]["RCLONE_CONFIG_IMAGES_ACCESS_KEY_ID"] == "key"
    assert url == "https://golem-distros.s3.gra.io.cloud.ovh.net/releases/v1.0.0.json"


def test_the_versioned_manifest_and_latest_do_not_collide_on_their_local_paths():
    files, runner = FakeFiles(), RecordingRunner()
    for key in ("releases/v1.0.0.json", "releases/latest.json"):
        publish_text('{"v": 1}', key, DESTINATION, WORKSPACE, runner, files)
    assert sorted(files.written) == [
        "/repo/output/latest.json",
        "/repo/output/v1.0.0.json",
    ]


def test_the_aws_environment_maps_our_settings_to_the_names_aws_reads():
    environment = aws_environment(DESTINATION)
    assert environment["AWS_ACCESS_KEY_ID"] == "key"
    assert environment["AWS_SECRET_ACCESS_KEY"] == "secret"
    assert environment["AWS_ENDPOINT_URL"] == "https://s3.gra.io.cloud.ovh.net"
    assert environment["AWS_REGION"] == "gra"


def test_the_access_check_lists_the_bucket():
    assert access_check_command("golem-distros") == (
        "aws",
        "s3",
        "ls",
        "s3://golem-distros",
    )
