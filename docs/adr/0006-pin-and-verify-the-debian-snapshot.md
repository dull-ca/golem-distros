# 0006. Pin and verify the Debian snapshot

## Status

Accepted.

## Context

Every image starts from the Debian Trixie generic cloud qcow2 file, the
largest input to a build.

Both source repositories fetch
`https://cloud.debian.org/images/cloud/trixie/latest/debian-13-generic-amd64.qcow2`.
Debian moves `latest` whenever it publishes a new snapshot, and neither
repository records which snapshot it got or checks a checksum. Two builds a
week apart can therefore differ with the same commit and no message, and a
rebuild of an old tag cannot reproduce the old image.

Debian publishes a `SHA512SUMS` file in every snapshot directory, so the
data needed to fix this exists.

## Decision

We pin the snapshot URL and its SHA-512 in `golem_distros/bases.py`. The
pinned value at v1.0.0 is:

```
url    https://cloud.debian.org/images/cloud/trixie/20260831-2587/debian-13-generic-amd64-20260831-2587.qcow2
sha512 5a069019420fb9441ad4f8004c661fadb747edd5662ca54a17c8f923dee7d717e21dbdaa4ba72d6fce7f920e0217f0a9af382298a7d46ed4bc9dc33ac19181b6
```

The build downloads the file, computes its SHA-512, and stops before
`virt-resize` on a mismatch. It verifies a cached file again on every build,
so it catches a damaged cache too.

Both configurations share one `BaseImage` value, so a pin move moves both at
once.

We reject `latest`. It is not a version, and it makes the base image an
untracked input.

We reject a pinned URL with no checksum. The URL proves which file we asked
for, not which bytes arrived.

We reject mirroring the base image in our own bucket. It removes the trust
problem, and it adds a second copy to keep and pay for.

## Consequences

The same commit fetches the same input bytes, so a rebuild of a tag differs
only where the build itself is not deterministic.

A base image change needs a commit, and Decision 0003 turns that commit into
a version bump.

No command moves the pin: a person edits `golem_distros/bases.py` by hand,
following the procedure in `CONTRIBUTING.md`. A pin nobody moves ages, and a
stale base ships stale packages.

Debian eventually removes old snapshot directories. When the pinned one
disappears, every build fails at the download, including a rebuild of an old
tag, and you recover by moving the pin, which means a new version and a new
image.

A corrupt or substituted download stops the build with a clear error. Do not
work around that stop.

A `golem-do` image ships the packages the pinned snapshot shipped. Nothing
upgrades them at build time, so the pin governs what lands in the image and a
rebuild of an old tag installs the same versions. The image enables
`unattended-upgrades`, so a booted host patches itself rather than relying on
the build to be recent.

The kernel comes from the pin too, on both configurations. The pinned base is
Debian's `generic` image rather than `genericcloud`, so it already carries the
generic kernel through the `linux-image-amd64` metapackage, and neither
configuration installs another one. That metapackage tracks Trixie, which is
what `unattended-upgrades` is configured to follow, so the kernel a host boots
keeps receiving security updates.

Installing a kernel from `trixie-backports` would break both halves of that.
It has to be named by exact version, so no metapackage tracks it, and
`Unattended-Upgrade::Origins-Pattern` matches only `trixie` and
`trixie-security`, so a backports kernel is never upgraded by any route. It
would also be selected from a moving index at build time, which is exactly what
this decision rejects for the base image.

`golem-ovh` still differs in one inherited way: `provision/30-baremetal.sh`
runs `apt-get -y dist-upgrade`, so that build's output bytes drift between
builds of the same pinned base. The kernel swap used to be the reason for it.
That reason is gone and the call has not been revisited.
