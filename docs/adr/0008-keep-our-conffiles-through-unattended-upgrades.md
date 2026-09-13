# 0008. Keep our conffiles through unattended upgrades

## Status

Accepted.

## Context

`provision/10-nftables.sh` writes the firewall into `/etc/nftables.conf`, which
dpkg tracks as a conffile of the `nftables` package. The file Debian ships is
not a firewall: it runs `flush ruleset`, which deletes every table in every
family, and then declares three base chains with no policy and no rules, so
everything is accepted on all three hooks. It is a skeleton for an
administrator to fill in, and the package does not even enable the service on a
first install.

Both images enable `unattended-upgrades`, and a modified conffile does not
produce a prompt there, because there is nobody to answer one. Its
`conffile_prompt` function compares the checksum dpkg recorded, the checksum on
disk and the checksum in the new package, and when all three differ the caller
adds the package to a blacklist, logs that it needs to be upgraded by hand, and
moves on. The first `nftables` upload that touched that file would therefore
have stopped `nftables` receiving security updates on every golem host, for as
long as the host lived.

There is no drop-in directory for nftables rules. `README.Debian` tells the
administrator to edit `/etc/nftables.conf`, and that is the whole supported
story, so every way of shipping a firewall in an image is a workaround of some
kind.

## Decision

We keep writing `/etc/nftables.conf`, and we stop the upgrade problem at its
source. `provision/00-base.sh` writes
`/etc/apt/apt.conf.d/90-golem-conffiles`:

```
DPkg::Options { "--force-confold"; };
```

`unattended-upgrade`'s `dpkg_conffile_prompt` returns false as soon as
`DPkg::Options` contains `--force-confold`, and the whole blacklisting block is
guarded by that call. So the package upgrades normally and our version of the
file survives. It reads the plain `DPkg::Options`, not an
unattended-upgrades-specific key, so the setting applies to every apt run on
the host.

The rules themselves stay in `/etc/nftables.d/*.conf`, which
`/etc/nftables.conf` includes. The entry file holds `add table inet filter` and
`flush table inet filter` rather than Debian's `flush ruleset`, so a reload
replaces our table and leaves any table podman, libvirt or a VPN created in
place. `lichess-sysadmin` runs the same arrangement, which is where it comes
from.

We reject leaving the conffile alone and redirecting the unit's `ExecStart` at
a file of our own. It keeps the conffile pristine, but it makes
`nft -f /etc/nftables.conf` — the gesture `README.Debian` tells an
administrator to make — load the stock ruleset and take the firewall down on a
live host. Overwriting the conffile makes that gesture safe.

We reject removing `unattended-upgrades`, which is how `lichess-sysadmin`
avoids the question. That works there because Ansible reconverges those hosts.
Nothing reconverges a golem host, so unattended patching is the only thing
keeping it current.

## Consequences

`nftables` keeps receiving unattended security upgrades, and keeps our rules.

`--force-confold` applies to every conffile and every apt invocation on the
host, not only to the firewall and not only to unattended runs. A future
provision step that modifies another conffile inherits the same protection
without anyone deciding so. An administrator running `apt upgrade` by hand is
not told that a conffile diverged either; the maintainer's version is written
alongside as `.dpkg-dist` and theirs is kept.

This decision covers conffiles only. Where a package ships a real drop-in
mechanism we use it rather than this: `provision/30-baremetal.sh` turns the
`growpart` and `resizefs` cloud-init modules off through
`/etc/cloud/cloud.cfg.d/92-golem-baremetal.cfg` and their own documented
switches, instead of deleting them from `/etc/cloud/cloud.cfg`. That also keeps
`cloud-init` out of the blacklist, and it does not depend on the apt setting
above.

`provision/30-baremetal.sh` edits `/etc/default/grub`, a conffile of
`grub-cloud-amd64`, but only after purging that package and restoring Debian's
stock file from `/usr/share/grub/default/grub`. By the time the edits happen no
package owns the file.
