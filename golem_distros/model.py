from dataclasses import dataclass
from enum import Enum

GOLEMD_SOURCE = "@golemd"


class SeedKind(str, Enum):
    NOCLOUD = "nocloud"
    CONFIG_DRIVE = "config-drive"


@dataclass(frozen=True)
class BaseImage:
    url: str
    sha512: str

    @property
    def filename(self) -> str:
        return self.url.rsplit("/", 1)[-1]


@dataclass(frozen=True)
class Payload:
    source: str
    destination: str
    mode: str | None = None


@dataclass(frozen=True)
class ProvisionStep:
    script: str
    payloads: tuple[Payload, ...] = ()


@dataclass(frozen=True)
class Distro:
    name: str
    base: BaseImage
    size: str
    root_partition: str
    steps: tuple[ProvisionStep, ...]
    seed: SeedKind
    payloads: tuple[Payload, ...] = ()
