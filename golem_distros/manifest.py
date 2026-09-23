import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass

from golem_distros.model import BaseImage


@dataclass(frozen=True)
class PublishedGolemd:
    flake: str
    rev: str


@dataclass(frozen=True)
class PublishedImage:
    url: str
    sha512: str
    checksum_url: str
    base: BaseImage


@dataclass(frozen=True)
class PublishedRelease:
    version: str
    released: str
    commit: str
    golemd: PublishedGolemd
    images: Mapping[str, PublishedImage]


def published_manifest_json(release: PublishedRelease) -> str:
    return json.dumps(asdict(release), indent=2) + "\n"
