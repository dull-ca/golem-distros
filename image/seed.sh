#!/usr/bin/env bash

set -euo pipefail

kind="$1"
hostname="$2"
user_data="$3"
directory="$4"
output="$5"

nocloud_seed() {
    mkdir -p "$directory"
    cp "$user_data" "$directory/user-data"
    printf 'instance-id: %s\nlocal-hostname: %s\n' "$hostname" "$hostname" \
        >"$directory/meta-data"
}

config_drive_seed() {
    mkdir -p "$directory/openstack/latest"
    cp "$user_data" "$directory/openstack/latest/user_data"
    printf '{\n  "uuid": "%s",\n  "hostname": "%s",\n  "name": "%s"\n}\n' \
        "$(uuidgen --sha1 --namespace @dns --name "$hostname")" "$hostname" "$hostname" \
        >"$directory/openstack/latest/meta_data.json"
}

case "$kind" in
nocloud)
    volume_id=cidata
    write_seed=nocloud_seed
    ;;
config-drive)
    volume_id=config-2
    write_seed=config_drive_seed
    ;;
*)
    echo "$kind is not a seed kind" >&2
    exit 2
    ;;
esac

rm -fr "$directory"
rm -f "$output"
"$write_seed"

genisoimage -output "$output" -volid "$volume_id" -joliet -rock "$directory"
