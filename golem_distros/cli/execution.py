import os
import shlex
import subprocess
from collections.abc import Callable, Mapping, Sequence

from golem_distros.ports import CommandFailed


class Subprocess:
    def run(self, argv: Sequence[str], env: Mapping[str, str] | None = None) -> None:
        merged = {**os.environ, **(env or {})}
        code = subprocess.call(list(argv), env=merged)
        if code != 0:
            raise CommandFailed(f"{shlex.join(argv)} exited {code}")

    def capture(self, argv: Sequence[str]) -> str:
        finished = subprocess.run(list(argv), capture_output=True, text=True)
        if finished.returncode != 0:
            raise CommandFailed(f"{shlex.join(argv)} exited {finished.returncode}")
        return finished.stdout


class DryRun:
    def __init__(self, write: Callable[[str], None]) -> None:
        self.write = write

    def run(self, argv: Sequence[str], env: Mapping[str, str] | None = None) -> None:
        self.write(shlex.join(argv))

    def capture(self, argv: Sequence[str]) -> str:
        self.write(shlex.join(argv))
        return ""
