from collections.abc import Mapping, Sequence
from typing import Protocol


class CommandFailed(Exception):
    pass


class Runner(Protocol):
    def run(self, argv: Sequence[str], env: Mapping[str, str] | None = None) -> None: ...

    def capture(self, argv: Sequence[str]) -> str: ...


class Files(Protocol):
    def exists(self, path: str) -> bool: ...

    def sha512(self, path: str) -> str: ...

    def write_text(self, path: str, text: str) -> None: ...
