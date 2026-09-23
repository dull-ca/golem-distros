from golem_distros.distros.digitalocean import GOLEM_DO
from golem_distros.distros.ovh import GOLEM_OVH
from golem_distros.model import Distro


class UnknownDistro(Exception):
    pass


REGISTRY: dict[str, Distro] = {distro.name: distro for distro in (GOLEM_DO, GOLEM_OVH)}


def names() -> list[str]:
    return sorted(REGISTRY)


def all_distros() -> list[Distro]:
    return [REGISTRY[name] for name in names()]


def find(name: str) -> Distro:
    try:
        return REGISTRY[name]
    except KeyError:
        raise UnknownDistro(f"{name} is not a configuration; try {', '.join(names())}")
