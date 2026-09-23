# 0003. Semantic versions from conventional commits

## Status

Accepted.

## Context

Every published image needs a version, and a consumer reads it to decide
whether an image is safe to roll out.

The images are not independent. `golem-ovh` and `golem-do` share the base
image, the golemd unit, the cloud-init and sshd configuration that admits
root by key and refuses passwords, and the nftables rules. A change to
`provision/05-cloud-init-root.sh` changes both.

The project writes conventional commits, so each subject already states the
kind of change it describes.

## Decision

We derive the next version from the commit subjects since the last `v*`
tag. `golem_distros/versioning.py` implements this, and it reads no file.

A `feat` raises the minor number. A `!` after the type or a
`BREAKING CHANGE:` footer raises the major number. Any other subject raises
the patch number. The largest bump in the range wins.

All configurations release together under one version, and no version is
skipped for a configuration that did not change. The first release is
`v1.0.0`, because no `v*` tag exists yet.

We reject a monotonic integer such as `build-118`. It orders releases, and
it tells nobody whether the user-data that boots the image must change.

We reject a date stamp such as `20260912`. Two releases in one day need a
suffix, and the suffix would have to carry the compatibility signal that the
date lacks.

## Consequences

A consumer can compare `v1.4.0` with `v2.0.0` and know that something
breaking happened.

Every configuration gets a new version at every release, even one that did
not change, so two versions of `golem-do` can contain the same bytes. The
`.sha512` sidecar makes that visible, and the storage cost is small.

A sloppy commit subject produces a wrong bump. An unrecognised type raises
the patch number, so the risk is a version that is too low, not too high.

`golem-distros release` refuses to run with no commits since the last tag,
because an empty range has no bump to compute.
