# golem-distros

This repository builds Debian Trixie images that cloud-init configures at
first boot. Each image contains the `golemd` agent, an sshd configuration that
accepts key-based root login and refuses passwords, and a default-drop
nftables firewall. No image contains a key or a secret. The consumer specifies
the SSH keys, the golem token and the golem secret key in cloud-init
user-data. The tool publishes each image as a qcow2 file in a public
S3-compatible bucket, because OVH and DigitalOcean install a custom
image by fetching a qcow2 over HTTP.

The repository builds images only. It creates no machines and renders no
cloud-config. The decision records under `docs/adr/` explain why it is built
this way, and `CONTRIBUTING.md` explains how to build, test and release it.

## First boot

The consumer supplies cloud-init user-data. Root is the cloud-init default
user, so cloud-init writes a top-level `ssh_authorized_keys` list to
`/root/.ssh/authorized_keys`, and the user-data needs no `users` block. sshd
rejects passwords, so a host that boots without a key is unreachable over SSH.

The `golemd` service is enabled but stays inactive until `/etc/golem/token`
and `/etc/golem/secret-key` exist. The user-data must write both files as
root with mode `0600`, then start `golemd.service`.

## Configurations

Each configuration is a frozen Python dataclass under `golem_distros/distros/`.
A build starts from the pinned Debian snapshot, creates an 8G disk, expands
the base root partition into it, runs the configuration's provision scripts in
declared order, and ends with `cloud-init clean --logs --seed` inside the
guest. Every configuration runs the same first steps. They upgrade the base
system, make root the cloud-init default user, disable password login, install
the firewall, and install `golemd`.
The firewall accepts established traffic, loopback, ICMP, and TCP port 22, and
drops everything else, forwarded traffic included. `/etc/nftables.conf` loads
`/etc/nftables.d/*.conf`, so a host adds rules by writing a file into that
directory and running `systemctl reload nftables`.

### DigitalOcean droplet

`golem-do` targets DigitalOcean droplets. Cloud-init reads the user-data from
the DigitalOcean metadata service. The image keeps the base snapshot's kernel,
the default datasource list, and the `growpart` and `resizefs` cloud-init
modules, so the filesystem grows to the droplet disk. It installs `do-agent`, because
DigitalOcean refuses to enable monitoring at create time on a droplet booted
from a custom image.

Import the image from its manifest URL as a custom image, create a droplet
from it, and pass this document as the droplet's user data:

```yaml
#cloud-config
ssh_authorized_keys:
  - ssh-ed25519 AAAA... you@example
write_files:
  - path: /etc/golem/token
    owner: root:root
    permissions: "0600"
    encoding: b64
    content: <base64 token>
  - path: /etc/golem/secret-key
    owner: root:root
    permissions: "0600"
    encoding: b64
    content: <base64 secret key>
runcmd:
  - [systemctl, start, golemd.service]
```

### OVH bare metal

`golem-ovh` targets OVH bare metal installed through BYOLinux. The image pins
`datasource_list: [ ConfigDrive, None ]`, so cloud-init reads the user-data
from a ConfigDrive at `openstack/latest/user_data` and ignores every other
source. It purges `grub-cloud-amd64` and installs `mdadm`, `lvm2`,
`btrfs-progs`, and CPU microcode. It keeps the base snapshot's kernel, which is
the generic flavour rather than the cloud one, because the pinned base is
Debian's `generic` image; the headers matching it and the grub and ZFS packages
are downloaded into the apt cache without being installed. It turns the
`growpart` and `resizefs` cloud-init modules off, because OVH partitions the
disk itself. It installs `kexec-tools`, and installs
`/root/.ovh/make_image_bootable.sh` with mode `0700`, which OVH runs during a
BYOLinux install.

A BYOLinux install takes the image URL and its SHA-512 from the manifest, and
builds a ConfigDrive from the data you supply. That drive holds two files.
`openstack/latest/meta_data.json` names the host, and `golemd` reports itself
under that hostname:

```json
{ "uuid": "0d4f8e2a-...", "hostname": "dull-01" }
```

`openstack/latest/user_data` holds the cloud-config:

```yaml
#cloud-config
ssh_authorized_keys:
  - ssh-ed25519 AAAA... you@example
write_files:
  - path: /etc/golem/token
    owner: root:root
    permissions: "0600"
    encoding: b64
    content: <base64 token>
  - path: /etc/golem/secret-key
    owner: root:root
    permissions: "0600"
    encoding: b64
    content: <base64 secret key>
runcmd:
  - [systemctl, start, golemd.service]
```

## The bucket

`GOLEM_DISTROS_IMAGE_BUCKET` and `GOLEM_DISTROS_IMAGE_REGION` name the bucket
and region a release writes to, and `GOLEM_DISTROS_IMAGE_ACL` sets the ACL on
every object. A release writes these keys:

```
<configuration>/<version>/<configuration>-<sha512[0:16]>.qcow2
<configuration>/<version>/<configuration>-<sha512[0:16]>.qcow2.sha512
releases/<version>.json
releases/latest.json
```

A public URL is `GOLEM_DISTROS_IMAGE_BASE_URL` followed by `/` and the key,
for example `https://golem-distros.s3.gra.io.cloud.ovh.net/<key>`. The file
name includes the first 16 hexadecimal characters of the image SHA-512, and
the `.sha512` file contains the full checksum in `sha512sum -c` format. OVH
and DigitalOcean both fetch an image anonymously over HTTP during an install,
so if `GOLEM_DISTROS_IMAGE_ACL` is `private`, something in front of the
bucket must serve those URLs.
`releases/latest.json` is the only object a release overwrites; a consumer
that pins a version reads `releases/<version>.json`. Both files look like
this:

```json
{
  "version": "v1.4.0",
  "released": "2026-09-12T20:31:04Z",
  "commit": "8f2c1ab...",
  "golemd": { "flake": "github:dull-ca/golem", "rev": "41bf030..." },
  "images": {
    "golem-ovh": {
      "url": "https://golem-distros.s3.gra.io.cloud.ovh.net/golem-ovh/v1.4.0/golem-ovh-a1b2c3d4e5f60718.qcow2",
      "sha512": "...",
      "checksum_url": "https://golem-distros.s3.gra.io.cloud.ovh.net/golem-ovh/v1.4.0/golem-ovh-a1b2c3d4e5f60718.qcow2.sha512",
      "base": { "url": "...", "sha512": "..." }
    },
    "golem-do": { "...": "..." }
  }
}
```

`commit` names the HEAD the images were built from, and `golemd.rev` records
which `golemd` the images contain. A consumer reads `releases/latest.json`
over HTTPS and needs no clone of this repository.
