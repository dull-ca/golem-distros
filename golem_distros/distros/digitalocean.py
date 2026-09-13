from golem_distros import steps
from golem_distros.bases import DEBIAN_TRIXIE
from golem_distros.model import Distro, SeedKind

GOLEM_DO = Distro(
    name="golem-do",
    base=DEBIAN_TRIXIE,
    size="8G",
    root_partition="/dev/sda1",
    steps=(
        steps.BASE,
        steps.CLOUD_INIT_ROOT,
        steps.NFTABLES,
        steps.GOLEMD,
        steps.DO_AGENT,
        steps.FINALISE,
    ),
    seed=SeedKind.NOCLOUD,
)
