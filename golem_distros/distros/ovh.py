from golem_distros import steps
from golem_distros.bases import DEBIAN_TRIXIE
from golem_distros.model import Distro, SeedKind

GOLEM_OVH = Distro(
    name="golem-ovh",
    base=DEBIAN_TRIXIE,
    size="8G",
    root_partition="/dev/sda1",
    steps=(
        steps.BASE,
        steps.BAREMETAL,
        steps.CLOUD_INIT_ROOT,
        steps.NFTABLES,
        steps.GOLEMD,
        steps.CONFIG_DRIVE,
        steps.KEXEC,
        steps.FINALISE,
    ),
    seed=SeedKind.CONFIG_DRIVE,
    payloads=(steps.OVH_BOOT_HOOK,),
)
