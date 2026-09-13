# 0004. One bucket, keyed by configuration and version

## Status

Accepted.

## Context

OVH fetches an image URL during a BYOLinux install, and DigitalOcean fetches
one to import a custom image. Neither can read a private object, so every
image object must be `public-read`.

The URL is often the only record of what a machine booted, so a person who
reads an install log must be able to name the release from the URL alone.

`strabs-iac` publishes one flat content-addressed name per image,
`strabs-base-<sha512[0:16]>.qcow2`, which contains no version. `dulliac`
publishes the fixed name `dull-base.qcow2`, which every build overwrites.

## Decision

We use one bucket, `golem-distros`, in a region set by configuration, and
upload with `rclone`, as both source repositories do.

We key every object by configuration, then version, then content hash:

```
golem-ovh/v1.4.0/golem-ovh-a1b2c3d4e5f60718.qcow2
golem-ovh/v1.4.0/golem-ovh-a1b2c3d4e5f60718.qcow2.sha512
golem-do/v1.4.0/golem-do-9f8e7d6c5b4a3928.qcow2
golem-do/v1.4.0/golem-do-9f8e7d6c5b4a3928.qcow2.sha512
releases/v1.4.0.json
releases/latest.json
```

The hash is the first 16 hexadecimal characters of the image SHA-512.

We reject the flat content-addressed name. It keeps the version out of the
URL, so a reader cannot trace a URL in a log to a release without a lookup.

We reject the fixed name. Every build overwrites the last, so no earlier
image survives a rebuild.

We reject a bucket per configuration. Separate buckets need separate ACL
settings, keys and lifecycle rules, and gain nothing.

## Consequences

A URL names its release: the path segment after the configuration name is
the version, and a person reads it without a tool.

The hash stays in the file name, so two different builds of one version
never collide.

Every object is world readable, so no image may ever contain a secret.
Decision 0005 keeps SSH keys out of the images.

An image is immutable at its key. You fix a bad release by publishing a new
version, never by overwriting.

`releases/latest.json` is the only object a release overwrites. A consumer
that reads it gets the newest release, and a consumer that pins a version
reads `releases/<version>.json`.

Old versions stay in the bucket and cost storage. Deleting one breaks any
host that reinstalls from that URL.
