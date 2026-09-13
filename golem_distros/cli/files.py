import hashlib
from collections.abc import Callable
from pathlib import Path

CHUNK = 1024 * 1024
PLACEHOLDER_DIGEST = "0" * 128


class LocalFiles:
    def exists(self, path: str) -> bool:
        return Path(path).exists()

    def sha512(self, path: str) -> str:
        digest = hashlib.sha512()
        with Path(path).open("rb") as handle:
            for chunk in iter(lambda: handle.read(CHUNK), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def write_text(self, path: str, text: str) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)


class DryRunFiles(LocalFiles):
    def __init__(self, write: Callable[[str], None]) -> None:
        self.write = write

    def sha512(self, path: str) -> str:
        self.write(f"sha512 {path}")
        return PLACEHOLDER_DIGEST

    def write_text(self, path: str, text: str) -> None:
        self.write(f"write {len(text)} bytes to {path}")
