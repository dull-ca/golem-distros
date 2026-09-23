import hashlib
from pathlib import Path

from rich.console import Console

from golem_distros.cli import announcing

CHUNK = 1024 * 1024


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
    def __init__(self, console: Console) -> None:
        self.console = console

    def sha512(self, path: str) -> str:
        announcing.render(["sha512", path], self.console)
        return super().sha512(path)

    def write_text(self, path: str, text: str) -> None:
        announcing.render(["write", str(len(text)), "bytes", "to", path], self.console)
