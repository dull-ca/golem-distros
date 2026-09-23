# 0007. This repository builds images only

## Status

Accepted.

## Context

The two source repositories each mix two jobs: each builds an image, and
each also creates machines with Pulumi and renders cloud-config for them.
`dulliac` drives OVH bare metal, and `strabs-iac` drives DigitalOcean
droplets.

The two jobs change at different rates and for different reasons. An image
changes when a package, a kernel, or a provision script changes; a fleet
changes when a host is added, moved, or retired. They also need different
rights: a build needs a write key for one bucket, while a fleet needs an API
token that can create and destroy machines. A cloud-config renderer sits
between the jobs, because it needs both the image's first-boot requirements
and each host's keys and secrets.

## Decision

This repository builds images, publishes them, and records releases. It does
nothing else. Out of scope: Pulumi, DNS, droplets, dedicated servers, fleet
manifests, and cloud-config rendering.

A separate `dull-cli` repository will own consumption. It reads
`releases/latest.json` from the bucket over HTTPS and needs no clone of this
repository. `dulliac` and `strabs-iac` keep their Pulumi code and stop
building images.

We reject shipping a cloud-config renderer here. A renderer needs per-host
secrets, so this repository would need a way to read them, and that would
put secrets next to a public bucket.

We reject one repository for everything. It would tie every fleet edit to
the image release cycle, so each one would bump an image version.

## Consequences

The boundary is a document, not a function call. `README.md` states what a
consumer must send at first boot — the SSH keys, the golem token and the
golem secret key — and Decision 0005 explains why. A consumer must satisfy
that itself, and no code stops it from sending the wrong cloud-config, so a
change to the first-boot requirements is a breaking change and needs a
major version under Decision 0003.

Nothing here verifies a consumer. The boot test checks our own example
seed, not `dull-cli`.

The release manifest is the interface: JSON at a stable URL, readable from
any language.

This repository needs one credential, the access key for the image bucket. It
contains no cloud API token, so a leak here cannot create or destroy a
machine.

`dull-cli` does not exist yet. Until it does, a person writes the
cloud-config by hand, against the first-boot section and the per-configuration
examples in `README.md`.
