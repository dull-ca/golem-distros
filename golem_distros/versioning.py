import re
from collections.abc import Sequence
from enum import IntEnum

from semver import Version

SUBJECT_PATTERN = re.compile(r"^(?P<type>[a-zA-Z]+)(?:\([^)]*\))?(?P<breaking>!)?:")
BREAKING_FOOTER = re.compile(r"^BREAKING[ -]CHANGE:", re.MULTILINE)
FEATURE_TYPE = "feat"
TAG_PREFIX = "v"
FIRST_VERSION = Version(1, 0, 0)


class MalformedVersion(Exception):
    pass


class NoCommitsSinceLastRelease(Exception):
    pass


class Bump(IntEnum):
    PATCH = 1
    MINOR = 2
    MAJOR = 3


def parse_version(text: str) -> Version:
    try:
        return Version.parse(text.strip().removeprefix(TAG_PREFIX))
    except ValueError as invalid:
        raise MalformedVersion(f"{text} is not a semantic version") from invalid


def tag_for(version: Version) -> str:
    return f"{TAG_PREFIX}{version}"


def bump_for_message(message: str) -> Bump:
    if BREAKING_FOOTER.search(message):
        return Bump.MAJOR
    matched = SUBJECT_PATTERN.match(message.splitlines()[0] if message else "")
    if matched is None:
        return Bump.PATCH
    if matched.group("breaking"):
        return Bump.MAJOR
    return Bump.MINOR if matched.group("type").lower() == FEATURE_TYPE else Bump.PATCH


def bump_for(messages: Sequence[str]) -> Bump:
    if not messages:
        raise NoCommitsSinceLastRelease("no commits since the last tag")
    return max(bump_for_message(message) for message in messages)


def next_version(last: Version | None, messages: Sequence[str]) -> Version:
    kind = bump_for(messages)
    return FIRST_VERSION if last is None else last.next_version(kind.name.lower())
