#!/usr/bin/env bash

set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

dry_run=""
if [ "${1-}" = "--dry-run" ]; then
    dry_run=yes
    shift
fi

name="$1"
base_url="$2"
base_sha512="$3"
size="$4"
root_partition="$5"
output="$6"
shift 6

in_repository() {
    case "$1" in
    /*) printf '%s\n' "$1" ;;
    *) printf '%s\n' "$root/$1" ;;
    esac
}

perform() {
    if [ -n "$dry_run" ]; then
        echo "$@"
    else
        "$@"
    fi
}

image="$output/$name.qcow2"
base="$output/${base_url##*/}"

customize=(virt-customize -a "$image")
while [ "$#" -gt 0 ]; do
    case "$1" in
    run)
        customize+=(--run "$(in_repository "$2")")
        shift 2
        ;;
    copy)
        source="$(in_repository "$2")"
        target="$3/${source##*/}"
        customize+=(--mkdir "$3" --copy-in "$source:$3" --chown "0:0:$target")
        if [ "$4" != "-" ]; then
            customize+=(--chmod "$4:$target")
        fi
        shift 4
        ;;
    *)
        echo "$1 is not a build action" >&2
        exit 2
        ;;
    esac
done

perform mkdir -p "$output"

if [ ! -e "$base" ]; then
    perform curl -fL --progress-bar -o "$base.partial" "$base_url"
    perform mv "$base.partial" "$base"
fi

if [ -z "$dry_run" ] && ! printf '%s  %s\n' "$base_sha512" "$base" | sha512sum --check --status; then
    echo "$base does not match the pinned checksum $base_sha512" >&2
    exit 1
fi

perform rm -f "$image"
perform qemu-img create -f qcow2 "$image" "$size"
perform virt-resize --expand "$root_partition" "$base" "$image"
perform "${customize[@]}"
perform qemu-img convert -O qcow2 -c "$image" "$image.compressed"
perform mv "$image.compressed" "$image"
perform chmod 0444 "$image"
