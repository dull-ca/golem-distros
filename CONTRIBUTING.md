# Contributing

We use devenv to provide the tools this repository needs. See `devenv.nix` for
the list. Follow https://devenv.sh/getting-started/ to install devenv, then run
`devenv shell` to start a development shell that contains all of them. To run
one command without starting that shell, prefix it with `devenv shell --`, as
in `devenv shell -- pytest -q`.

Run `pytest -q` for the test suite. It never builds or boots an image, so a
passing run does not mean your change works. Boot the image too, as described
below.

Write code that explains itself. A pull request needs no comments, and
reviewers may criticise over-commenting. Use review to find the places where a
comment earns its keep: when someone asks a question about a piece of code,
first try to change the code so the question does not arise. If that is hard
or impossible, write a comment that answers it. Reasoning about a design
decision belongs in a record under `docs/adr/` rather than in a source file.

No comment may be written by an LLM. See [AI_POLICY.md](AI_POLICY.md).

Write conventional commits, because `golem-distros release` reads them to
derive the next version. A `feat` raises the minor number, a `!` or a
`BREAKING CHANGE` footer raises the major number, and anything else raises the
patch number.

## AI usage

This project has strict rules for AI usage. Read
[AI_POLICY.md](AI_POLICY.md) before you contribute. **This is very important.**

## Commands

`golem-distros list` prints every configuration name, one per line.

`golem-distros build <name> [--dry-run]` runs `image/build.sh`, the one build
path every configuration shares. It downloads the base image if the cache
lacks it, verifies it against the pinned SHA-512, creates the disk, runs the
provision scripts, and compresses the result to `output/<name>.qcow2`. Python
passes the configuration's values and its ordered actions; the script builds
the command lines. A real build needs `GOLEM_DISTROS_GOLEMD`. `--dry-run`
prints every command instead of running it, so you can use it on a machine
with none of the tools installed.

`golem-distros boot <name> [--seed <file>] [--memory <megabytes>] [--direct]`
boots the built image under `qemu-system-x86_64` with `snapshot=on`. `--memory`
defaults to 2048. QEMU writes the console to your terminal, and uses KVM when
`/dev/kvm` is readable and writable. Press `Ctrl-a` then `x` to exit it.
`--direct` runs `image/direct_boot.sh` first, which reads the image's
`grub.cfg`, copies the kernel and initrd out, and boots them with a serial
console added, so you see the boot from the first line instead of from GRUB.

`golem-distros publish <name> --version <version> [--dry-run]` uploads one
built image and its `.sha512` sidecar with rclone. Pass the full tag to
`--version`, such as `v1.4.0`. A real upload needs the object storage settings
from `secretspec.toml`, set with `secretspec set <NAME>` and supplied through
`secretspec run --`. `--dry-run` prints the rclone commands with placeholder
credentials.

`golem-distros release` takes no options. It stops on a dirty tree, derives the
next semantic version from the conventional commits since the last `v*` tag,
builds every configuration, uploads each image and sidecar, writes and uploads
`releases/<version>.json` and the same bytes as `releases/latest.json`, then
commits the manifest and tags the commit. You push the tag yourself. The bucket
and an access key must exist before the first release.

## Testing an image

`golem-distros boot <name> --seed <file>` reads a cloud-config file and runs
`image/seed.sh`, which builds a throwaway seed image of the kind that
configuration needs, NoCloud for `golem-do` and ConfigDrive for `golem-ovh`, and
attaches it to the boot. QEMU discards every write, so the image itself is
unchanged. Log in at the console, read `/root/.ssh/authorized_keys` to confirm
cloud-init wrote the key, and run `systemctl status golemd` to confirm the agent
started.

## Adding a configuration

Write the provision scripts under `provision/` with a number prefix matching
the order they run in, add a `ProvisionStep` for each to
`golem_distros/steps.py`, build
a frozen `Distro` value in `golem_distros/distros/<target>.py`, and add it to
the registry tuple in `golem_distros/distros/__init__.py`. Nothing goes in
`image/build.sh`: every configuration shares it, so a step that only one
configuration needs belongs in `provision/`. A platform that reads a seed the
two existing kinds do not cover needs a new `SeedKind` and a new branch in
`image/seed.sh`. Add tests, run the suite, read the commands with `--dry-run`,
then build the image and boot it with a seed. The name becomes a directory in
the bucket and never changes.

## Moving the Debian pin

There is no `golem-distros base pin` verb. Choose a snapshot directory under
`https://cloud.debian.org/images/cloud/trixie/`, fetch its `SHA512SUMS` file,
and take the line for the generic amd64 qcow2,
`debian-13-generic-amd64-<snapshot>.qcow2`. Edit `golem_distros/bases.py` by
hand: set `url` to the image URL for that snapshot and `sha512` to the 128
hexadecimal characters from that line. Run the tests, then build and boot every
configuration, because a new base can change the kernel and packages. Commit
with a conventional subject so the next release bumps the version. Debian
eventually removes old snapshot directories. When the pinned one disappears the
download fails, and you fix it by moving the pin again.
