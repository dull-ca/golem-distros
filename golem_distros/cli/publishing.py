import os
from dataclasses import dataclass

from golem_distros import naming
from golem_distros.cli.building import BuiltImage
from golem_distros.cli.workspace import Workspace
from golem_distros.ports import Files, Runner

VARIABLES = {
    "bucket": "GOLEM_DISTROS_IMAGE_BUCKET",
    "region": "GOLEM_DISTROS_IMAGE_REGION",
    "endpoint": "GOLEM_DISTROS_IMAGE_ENDPOINT",
    "base_url": "GOLEM_DISTROS_IMAGE_BASE_URL",
    "provider": "GOLEM_DISTROS_IMAGE_PROVIDER",
    "acl": "GOLEM_DISTROS_IMAGE_ACL",
    "access_key_id": "GOLEM_DISTROS_IMAGES_ACCESS_KEY_ID",
    "secret_access_key": "GOLEM_DISTROS_IMAGES_SECRET_ACCESS_KEY",
}
SECRET_FIELDS = ("access_key_id", "secret_access_key")
REMOTE = "images"
UPLOAD_OPTIONS = (
    "--s3-upload-concurrency",
    "4",
    "--s3-chunk-size",
    "16M",
    "--progress",
    "--stats-one-line",
)


class MissingCredentials(Exception):
    pass


@dataclass(frozen=True)
class Destination:
    bucket: str
    region: str
    endpoint: str
    base_url: str
    provider: str
    acl: str
    access_key_id: str
    secret_access_key: str

    @classmethod
    def from_environment(cls) -> "Destination":
        values = {field: os.environ.get(name, "") for field, name in VARIABLES.items()}
        missing = [VARIABLES[field] for field, value in values.items() if not value]
        if missing:
            raise MissingCredentials(
                f"publishing needs {', '.join(missing)}; set them with secretspec"
            )
        return cls(**values)

    @classmethod
    def without_credentials(cls) -> "Destination":
        return cls(
            **{
                field: f"${name}"
                if field in SECRET_FIELDS
                else os.environ.get(name, f"${name}")
                for field, name in VARIABLES.items()
            }
        )


@dataclass(frozen=True)
class PublishedImage:
    url: str
    checksum_url: str
    sha512: str


def rclone_environment(destination: Destination) -> dict[str, str]:
    return {
        "RCLONE_CONFIG_IMAGES_TYPE": "s3",
        "RCLONE_CONFIG_IMAGES_PROVIDER": destination.provider,
        "RCLONE_CONFIG_IMAGES_ENDPOINT": destination.endpoint,
        "RCLONE_CONFIG_IMAGES_REGION": destination.region,
        "RCLONE_CONFIG_IMAGES_ACCESS_KEY_ID": destination.access_key_id,
        "RCLONE_CONFIG_IMAGES_SECRET_ACCESS_KEY": destination.secret_access_key,
        "RCLONE_CONFIG_IMAGES_ACL": destination.acl,
    }


def aws_environment(destination: Destination) -> dict[str, str]:
    return {
        "AWS_ACCESS_KEY_ID": destination.access_key_id,
        "AWS_SECRET_ACCESS_KEY": destination.secret_access_key,
        "AWS_ENDPOINT_URL": f"https://{destination.endpoint}",
        "AWS_REGION": destination.region,
    }


def access_check_command(bucket: str) -> tuple[str, ...]:
    return ("aws", "s3", "ls", f"s3://{bucket}")


def upload(source: str, key: str, destination: Destination, runner: Runner) -> str:
    target = f"{REMOTE}:{destination.bucket}/{key}"
    runner.run(
        ("rclone", "copyto", source, target, *UPLOAD_OPTIONS),
        rclone_environment(destination),
    )
    return naming.public_url(destination.base_url, key)


def publish_image(
    built: BuiltImage,
    version: str,
    destination: Destination,
    workspace: Workspace,
    runner: Runner,
    files: Files,
) -> PublishedImage:
    if not files.exists(built.path):
        raise FileNotFoundError(f"no image at {built.path}; build it first")
    key = naming.image_key(built.distro_name, version, built.sha512)
    name = naming.published_name(key)
    sidecar = f"{workspace.output}/{name}{naming.CHECKSUM_SUFFIX}"
    files.write_text(sidecar, naming.sidecar(built.sha512, name))
    checksum_key = key + naming.CHECKSUM_SUFFIX
    return PublishedImage(
        url=upload(built.path, key, destination, runner),
        checksum_url=upload(sidecar, checksum_key, destination, runner),
        sha512=built.sha512,
    )


def publish_text(
    text: str,
    key: str,
    destination: Destination,
    workspace: Workspace,
    runner: Runner,
    files: Files,
) -> str:
    local = f"{workspace.output}/{naming.published_name(key)}"
    files.write_text(local, text)
    return upload(local, key, destination, runner)
