from collections.abc import Mapping, Sequence
from pathlib import Path

from golem_distros.cli.publishing import Destination
from golem_distros.cli.workspace import Workspace

WORKSPACE = Workspace(root="/repo", output="/repo/output")
DESTINATION = Destination(
    bucket="golem-distros",
    region="gra",
    endpoint="s3.gra.io.cloud.ovh.net",
    base_url="https://golem-distros.s3.gra.io.cloud.ovh.net",
    provider="Other",
    acl="public-read",
    access_key_id="key",
    secret_access_key="secret",
)


def stub_binaries(directory: Path, bodies: Mapping[str, str]) -> str:
    directory.mkdir(parents=True)
    for name, body in bodies.items():
        stub = directory / name
        stub.write_text(
            f'#!/usr/bin/env bash\necho "{name} $*" >> "$COMMAND_LOG"\n{body}'
        )
        stub.chmod(0o755)
    return str(directory)


class RecordingRunner:
    def __init__(self, outputs: Mapping[str, str] | None = None) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.environments: list[Mapping[str, str] | None] = []
        self.outputs = dict(outputs or {})

    def run(self, argv: Sequence[str], env: Mapping[str, str] | None = None) -> None:
        self.calls.append(tuple(argv))
        self.environments.append(env)

    def capture(self, argv: Sequence[str]) -> str:
        self.calls.append(tuple(argv))
        return self.outputs.get(argv[0], "")


class FakeFiles:
    def __init__(
        self,
        present: Sequence[str] = (),
        digests: Mapping[str, str] | None = None,
    ) -> None:
        self.present = set(present)
        self.digests = dict(digests or {})
        self.written: dict[str, str] = {}

    def exists(self, path: str) -> bool:
        return path in self.present or path in self.written

    def sha512(self, path: str) -> str:
        return self.digests.get(path, "0" * 128)

    def write_text(self, path: str, text: str) -> None:
        self.written[path] = text
