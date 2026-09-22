#!/bin/bash

set -euxo pipefail

rm -f /etc/resolv.conf
echo "nameserver 213.186.33.99" >/etc/resolv.conf

export DEBIAN_FRONTEND=noninteractive

apt-get update

rm -f /etc/mdadm.conf
/usr/share/mdadm/mkconf force-generate

console_parameters="$(grep -Po '\bconsole=\S+' /proc/cmdline | paste -s -d" ")"
if ! grep '^GRUB_CMDLINE_LINUX="' /etc/default/grub | grep -qF "$console_parameters"; then
    sed -Ei "s/(^GRUB_CMDLINE_LINUX=.*)\"\$/\1 $console_parameters\"/" /etc/default/grub
fi

if lsblk -lno FSTYPE | grep -qxiF zfs_member; then
    release="$(ls -1 /boot/vmlinuz-* | sed 's|.*/vmlinuz-||' | sort -V | tail -1)"
    apt-get -y install --no-install-recommends "linux-headers-${release}" zfs-dkms zfs-initramfs zfs-zed
    systemctl enable zfs-import-scan.service
fi

if [ -d /sys/firmware/efi ]; then
    apt-get -y install --no-install-recommends grub-efi-amd64
    grub-install --target=x86_64-efi --efi-directory=/boot/efi --no-nvram
    apt-get -y purge grub-pc-bin
else
    realBootDevicesById=()
    read -r bootDevice bootDeviceType < <(findmnt -A -c -e -l -n -T /boot/ -o SOURCE,FSTYPE)
    if [[ "$bootDeviceType" == "zfs" ]]; then
        bootDevices="$(zpool status -LP "${bootDevice%/*}" | grep -Po '/dev/\S+')"
    else
        bootDevices="$bootDevice"
    fi
    realBootDevices="$(lsblk -n -p -b -l -o TYPE,NAME "$bootDevices" -s | awk '$1 == "disk" && !seen[$2]++ {print $2}')"
    for realBootDevice in $realBootDevices; do
        realBootDevicesById+=($(find -L /dev/disk/by-id/ -type b -samefile "$realBootDevice" | sort -us | head -n1))
    done
    echo "grub-pc grub-pc/install_devices multiselect $(sed 's/ /, /g' <<<"${realBootDevicesById[@]}")" | debconf-set-selections
    apt-get -y install --no-install-recommends grub-pc
    apt-get -y purge grub-efi-amd64-bin
fi

apt-get -y autoremove
apt-get -y clean

systemd-machine-id-setup
update-initramfs -u

update-grub

rm -fr /root/.ovh/
