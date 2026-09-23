# 0002. Configurations are typed code

## Status

Accepted.

## Context

A configuration records the base image, the disk size, the root partition,
the ordered provision steps, the seed kind, and the payload files.
`golem-ovh` and `golem-do` each need one.

A build takes minutes: it downloads a base image, then runs `virt-resize`
and `virt-customize`. A configuration error that surfaces late costs that
whole time, so before a build starts we want proof that every step script
exists on disk and every payload source resolves.

## Decision

We write each configuration as a frozen Python dataclass in
`golem_distros/distros/`, built from the `Distro`, `BaseImage`,
`ProvisionStep` and `Payload` classes in `golem_distros/model.py`. A
configuration is therefore a value that the type checker reads and the test
suite imports. `tests/test_distros.py` proves that names are unique, that
each step script exists, and that each payload source resolves.

We reject a TOML or YAML file read at run time. A misspelled key in such a
file goes undetected until the build parses it, after the download.

We reject a plugin directory that the tool scans at run time. A registry
this small does not need discovery.

## Consequences

A typo fails in `pytest`, in under a second, not in a build.

The registry in `golem_distros/distros/__init__.py` lists every
configuration by hand, so a new configuration needs a code change and a new
import, and a person who is not a Python programmer cannot add one by
editing a data file. The dataclasses are short and flat, so the cost is
small.

Configurations ship inside the package, so a user cannot add one at run time
without a fork. That is intended: a release builds every configuration in
the registry, and an unknown configuration has no release history.

## Amendment: typed configurations, but not typed command lines

This record was read as deciding that Python also assembles the build's
command lines. It does not. A configuration stays a frozen dataclass, and
`tests/test_distros.py` still proves each step script and payload source
resolves before a build starts.

Turning those values into `curl`, `qemu-img`, `virt-resize` and
`virt-customize` arguments now happens in `image/build.sh`, one script that
every configuration shares. Python passes the name, the base URL, the base
SHA-512, the size, the root partition, and the ordered `run` and `copy`
actions. It builds no argv, so the tests that pinned exact argv are gone,
and the guarantees they claimed — the checksum verified before any
`qemu-img` or `virt-customize` runs, and each payload copied in immediately
before the step that needs it — are proven by running the script against
stub binaries on `PATH`.

A build script per configuration stays rejected. `rm -f /etc/machine-id` was
fixed in one path and forgotten in the other once already.

The seed follows the same boundary. `SeedKind` stays part of the configuration,
so a typo still fails in `pytest`, but `image/seed.sh` writes the NoCloud and
ConfigDrive layouts and runs `genisoimage`. Python passes the kind, the
hostname, the cloud-config file, the staging directory and the image path. The
guarantees the Python modelling claimed — `cidata` for NoCloud, `config-2` under
`openstack/latest/` for ConfigDrive — are proven by running the script against a
stub `genisoimage`.
