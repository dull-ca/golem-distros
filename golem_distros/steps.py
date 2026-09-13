from golem_distros.model import GOLEMD_SOURCE, Payload, ProvisionStep

BASE = ProvisionStep("provision/00-base.sh")
CLOUD_INIT_ROOT = ProvisionStep("provision/05-cloud-init-root.sh")
NFTABLES = ProvisionStep("provision/10-nftables.sh")
GOLEMD = ProvisionStep("provision/20-golemd.sh", (Payload(GOLEMD_SOURCE, "/tmp"),))
BAREMETAL = ProvisionStep("provision/30-baremetal.sh")
CONFIG_DRIVE = ProvisionStep("provision/31-config-drive.sh")
KEXEC = ProvisionStep("provision/32-kexec.sh")
DO_AGENT = ProvisionStep("provision/40-do-agent.sh")
FINALISE = ProvisionStep("provision/90-finalise.sh")

OVH_BOOT_HOOK = Payload("files/ovh/make_image_bootable.sh", "/root/.ovh", "0700")
