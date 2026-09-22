#!/bin/bash

set -euxo pipefail

export DEBIAN_FRONTEND=noninteractive

apt-get -y purge grub-cloud-amd64
cp /usr/share/grub/default/grub /etc/default/grub

sed -i "s/\bmain\b/& contrib non-free non-free-firmware/" /etc/apt/sources.list.d/debian.sources 2>/dev/null \
    || sed -i "s/\bmain\b/& contrib non-free non-free-firmware/" /etc/apt/sources.list

apt-get update

apt-get -y install --no-install-recommends mdadm lvm2 patch btrfs-progs amd64-microcode intel-microcode
apt-get -y dist-upgrade

release="$(ls -1 /boot/vmlinuz-* | sed 's|.*/vmlinuz-||' | sort -V | tail -1)"
apt-get -y install --no-install-recommends --download-only "linux-headers-${release}" zfs-dkms zfs-initramfs zfs-zed

apt-get -y install --no-install-recommends --download-only grub-efi-amd64
apt-get -y install --no-install-recommends --download-only grub-pc
echo "grub-efi-amd64 grub2/update_nvram boolean false" | debconf-set-selections

cat >/etc/cloud/cloud.cfg.d/92-golem-baremetal.cfg <<'EOF'
growpart:
  mode: 'off'
resize_rootfs: false
EOF
chmod 0644 /etc/cloud/cloud.cfg.d/92-golem-baremetal.cfg

sed -i 's/^GRUB_CMDLINE_LINUX_DEFAULT=.*/GRUB_CMDLINE_LINUX_DEFAULT=""/' /etc/default/grub
sed -i 's/^GRUB_CMDLINE_LINUX=.*/GRUB_CMDLINE_LINUX="nomodeset iommu=pt"/' /etc/default/grub
echo 'GRUB_GFXPAYLOAD_LINUX="text"' >>/etc/default/grub

rm -f /etc/default/grub.d/10_cloud.cfg
rm -f /etc/default/grub.d/15_timeout.cfg
