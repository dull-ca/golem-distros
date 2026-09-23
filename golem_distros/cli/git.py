from collections.abc import Sequence

from golem_distros.ports import Runner
from golem_distros.releasing import RepositoryState
from golem_distros.versioning import MalformedVersion, parse_version

MESSAGE_SEPARATOR = "\x00"


class Git:
    def __init__(self, runner: Runner, root: str) -> None:
        self.runner = runner
        self.root = root

    def git(self, *arguments: str) -> str:
        return self.runner.capture(("git", "-C", self.root, *arguments))

    def run(self, *arguments: str) -> None:
        self.runner.run(("git", "-C", self.root, *arguments))

    def status_lines(self) -> tuple[str, ...]:
        raw = self.git("status", "--porcelain")
        return tuple(line for line in raw.splitlines() if line.strip())

    def tags(self) -> frozenset[str]:
        return frozenset(self.git("tag", "--list", "v*").split())

    def last_version_tag(self) -> str | None:
        candidates = []
        for name in self.tags():
            try:
                candidates.append((parse_version(name), name))
            except MalformedVersion:
                continue
        return max(candidates)[1] if candidates else None

    def messages_since(self, tag: str | None) -> tuple[str, ...]:
        span = "HEAD" if tag is None else f"{tag}..HEAD"
        raw = self.git("log", span, "--format=%B%x00")
        return tuple(
            part.strip() for part in raw.split(MESSAGE_SEPARATOR) if part.strip()
        )

    def head(self) -> str:
        return self.git("rev-parse", "HEAD").strip()

    def add(self, paths: Sequence[str]) -> None:
        self.run("add", *paths)

    def commit(self, message: str) -> None:
        self.run("commit", "-m", message)

    def tag(self, name: str) -> None:
        self.run("tag", name)


def repository_state(git: Git) -> RepositoryState:
    last = git.last_version_tag()
    status = git.status_lines()
    return RepositoryState(
        dirty=bool(status),
        last_tag=last,
        messages=git.messages_since(last),
        tags=git.tags(),
        head=git.head(),
        status=status,
    )
