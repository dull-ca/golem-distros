#!/usr/bin/env bash

set -euo pipefail

image="$1"
destination="$2"

grub_configuration=/boot/grub/grub.cfg
console=console=ttyS0,115200

entry="$(virt-cat -a "$image" "$grub_configuration" | awk -v console="$console" '
    $1 == "linux" && kernel == "" {
        kernel = $2
        for (field = 3; field <= NF; field++) arguments = arguments $field " "
    }
    $1 == "initrd" && kernel != "" {
        print kernel
        print $2
        print arguments console
        exit
    }
')"

if [ -z "$entry" ]; then
    echo "$grub_configuration names no kernel and initrd to boot directly" >&2
    exit 1
fi

{
    read -r kernel
    read -r initrd
    read -r command_line
} <<<"$entry"

mkdir -p "$destination"
rm -f "$destination/${kernel##*/}" "$destination/${initrd##*/}"
virt-copy-out -a "$image" "$kernel" "$initrd" "$destination" >&2

printf '%s\n%s\n%s\n' \
    "$destination/${kernel##*/}" \
    "$destination/${initrd##*/}" \
    "$command_line"
