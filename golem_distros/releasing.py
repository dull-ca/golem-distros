from dataclasses import dataclass

from semver import Version

from golem_distros.versioning import next_version, parse_version, tag_for


class DirtyWorkingTree(Exception):
    pass


class TagAlreadyExists(Exception):
    pass


@dataclass(frozen=True)
class RepositoryState:
    dirty: bool
    last_tag: str | None
    messages: tuple[str, ...]
    tags: frozenset[str]
    head: str
    status: tuple[str, ...] = ()


def plan_release(state: RepositoryState) -> Version:
    if state.dirty:
        raise DirtyWorkingTree(
            f"commit or stash your changes before you release: {', '.join(state.status)}"
        )
    last = None if state.last_tag is None else parse_version(state.last_tag)
    target = next_version(last, state.messages)
    if tag_for(target) in state.tags:
        raise TagAlreadyExists(f"{tag_for(target)} already exists")
    return target
