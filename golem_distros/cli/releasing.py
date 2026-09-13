from collections.abc import Mapping
from typing import Any

from golem_distros import distros, naming
from golem_distros.cli.building import build_image
from golem_distros.cli.publishing import Destination, publish_image, publish_text
from golem_distros.cli.workspace import Workspace
from golem_distros.manifest import (
    PublishedGolemd,
    PublishedImage,
    PublishedRelease,
    published_manifest_json,
)
from golem_distros.ports import Files, Runner
from golem_distros.releasing import RepositoryState, plan_release
from golem_distros.versioning import tag_for

RELEASE_MESSAGE = (
    "chore(release): {version}\n\n"
    "This release builds every configuration and uploads it. "
    "The manifest records each URL and each checksum."
)


def golemd_input(lock: Mapping[str, Any]) -> tuple[str, str]:
    locked = lock["nodes"]["golem"]["locked"]
    return f"{locked['type']}:{locked['owner']}/{locked['repo']}", locked["rev"]


def run_release(
    state: RepositoryState,
    workspace: Workspace,
    destination: Destination,
    golemd: str,
    lock: Mapping[str, Any],
    released_at: str,
    runner: Runner,
    files: Files,
    git,
) -> PublishedRelease:
    version = tag_for(plan_release(state))
    flake, revision = golemd_input(lock)
    built = [
        build_image(distro, workspace, golemd, runner, files)
        for distro in distros.all_distros()
    ]
    records: dict[str, PublishedImage] = {}
    for distro, image in zip(distros.all_distros(), built):
        published = publish_image(image, version, destination, workspace, runner, files)
        records[distro.name] = PublishedImage(
            url=published.url,
            sha512=published.sha512,
            checksum_url=published.checksum_url,
            base=distro.base,
        )
    release = PublishedRelease(
        version, released_at, state.head, PublishedGolemd(flake, revision), records
    )
    document = published_manifest_json(release)
    for key in (naming.manifest_key(version), naming.LATEST_KEY):
        publish_text(document, key, destination, workspace, runner, files)
    files.write_text(f"{workspace.root}/{naming.manifest_key(version)}", document)
    git.add([naming.RELEASES_DIRECTORY])
    git.commit(RELEASE_MESSAGE.format(version=version))
    git.tag(version)
    return release
