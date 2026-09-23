# 0005. SSH keys arrive at first boot

## Status

Accepted.

## Context

Every image must let an operator log in as root over SSH. The question is
when the trusted public keys enter the image.

Both source repositories bake them in at build time: each copies
`ssh-keys/*.pub` into `/etc/ssh/authorized_keys.d/root` inside the guest, so
the keys are part of the qcow2 file. A baked key fixes the set of people who
can log in at build time, makes a key rotation cost a new image, puts a list
of trusted keys into an object that Decision 0004 makes world readable, and
gives a consumer no way to add one key for one host.

Both source repositories also try to disable the cloud-init module that
would overwrite the baked key at first boot, by running this line inside the
guest:

```
sed -Ei '/^ - (users_groups|set_passwords)/d' /etc/cloud/cloud.cfg
```

That line never matched anything, because Debian's `/etc/cloud/cloud.cfg`
spells the module names with hyphens: `users-groups` and `set-passwords`.
Both repositories therefore shipped baked keys with the overwriting module
still active.

The images also need two secrets at first boot, `/etc/golem/token` and
`/etc/golem/secret-key`. Those can never be baked, so a first-boot channel
must exist anyway.

## Decision

No image contains an SSH key. The consumer sends the keys at first boot, in
cloud-init user-data.

We keep the `users_groups` and `set_passwords` cloud-init modules enabled.
`provision/30-baremetal.sh` does edit the module list in
`/etc/cloud/cloud.cfg`, but only to remove `grub-dpkg`, `growpart` and
`resizefs` on OVH bare metal, and its `sed` line matches because none of
those names contains an underscore.

We make root the cloud-init default user.
`provision/05-cloud-init-root.sh` writes
`/etc/cloud/cloud.cfg.d/90-golem.cfg`:

```yaml
disable_root: false
ssh_pwauth: false
system_info:
  default_user:
    name: root
    lock_passwd: true
    shell: /bin/bash
```

cloud-init therefore writes a plain top-level `ssh_authorized_keys` list to
`/root/.ssh/authorized_keys`, and the consumer writes no `users` block.

Two facts about cloud-init's config merge make this work. Its `read_conf_d`
sorts the files in `/etc/cloud/cloud.cfg.d/` in reverse filename order, and
its `mergemanydict` keeps the first value it sees for each key, so
`90-golem.cfg` beats `01_debian_cloud.cfg` for any key both files set. And
`disable_root: false` must accompany `default_user.name: root`: with
`disable_root` left `true`, cloud-init disables the very account the login
depends on.

The same script writes `/etc/ssh/sshd_config.d/90-golem.conf`:

```
PermitRootLogin prohibit-password
PasswordAuthentication no
KbdInteractiveAuthentication no
```

Debian's `sshd_config` includes `sshd_config.d/*.conf` on its first line,
and OpenSSH takes the first match for a keyword, so the drop-in wins over
anything cloud-init writes later in the main file.

We reject the baked key, for the costs in the context above. The inert `sed`
line never made it work in the source repositories, and this decision does
not depend on that line either way.

We reject a non-root default user with `sudo`. `golemd` reconciles the host
and reads `/etc/golem`, which is mode `0700` and owned by root. A second
account would add a privilege step and one more thing to manage, and it
would grant no authority that root does not already hold.

## Consequences

An image contains no secret and no identity, so the same public object is
safe for every consumer.

Key rotation needs a new boot, not a new build, and each host can get its
own key list.

The golemd unit keeps its two `ConditionPathExists` guards, so it stays
inactive until `/etc/golem/token` and `/etc/golem/secret-key` exist. The
consumer supplies the keys and both files in the same user-data.

Root as the cloud-init default user is uncommon. Most cloud images create a
normal user such as `debian`, and this record explains why these images do
not.

A host that boots with no `ssh_authorized_keys` is unreachable over SSH,
because password and keyboard-interactive login are off. The recovery is a
console or a reinstall.

Only a boot proves this works. `golem-distros boot <config> --seed
<cloud-config.yaml>` boots the image under QEMU with a throwaway seed, and a
person must confirm that the key lands in `/root/.ssh/authorized_keys`. No
unit test can prove it, because cloud-init must run.

The seed kind must match the datasource: `golem-do` takes a NoCloud seed,
and `golem-ovh` pins `datasource_list: [ ConfigDrive, None ]`, so it takes a
ConfigDrive seed. cloud-init ignores a wrong seed kind in silence, and the
host then has no keys.
