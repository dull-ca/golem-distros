import pytest
from semver import Version

from golem_distros.versioning import (
    Bump,
    MalformedVersion,
    NoCommitsSinceLastRelease,
    bump_for,
    next_version,
    parse_version,
    tag_for,
)


@pytest.mark.parametrize("text", ["v1.4.0", "1.4.0"])
def test_a_version_parses_with_or_without_a_leading_v(text):
    assert parse_version(text) == Version(1, 4, 0)


@pytest.mark.parametrize("text", ["v1.4", "v01.4.0", "v1.4.0.1", "v1.4.0rc1"])
def test_a_malformed_version_raises(text):
    with pytest.raises(MalformedVersion):
        parse_version(text)


def test_a_version_prints_with_a_leading_v():
    assert tag_for(Version(2, 0, 1)) == "v2.0.1"


@pytest.mark.parametrize(
    "message,expected",
    [
        ("chore: tidy", Version(1, 4, 4)),
        ("feat: add", Version(1, 5, 0)),
        ("feat!: replace", Version(2, 0, 0)),
    ],
)
def test_a_bump_clears_every_lower_number(message, expected):
    assert next_version(Version(1, 4, 3), [message]) == expected


@pytest.mark.parametrize(
    "message,expected",
    [
        ("feat: add the ovh configuration", Bump.MINOR),
        ("feat(ovh): add kexec", Bump.MINOR),
        ("fix: correct the firewall rule", Bump.PATCH),
        ("chore: tidy up", Bump.PATCH),
        ("not a conventional subject", Bump.PATCH),
        ("feat!: drop the debian user", Bump.MAJOR),
        ("refactor(cli)!: rename the build verb", Bump.MAJOR),
        ("fix: move it\n\nBREAKING CHANGE: consumers must update.", Bump.MAJOR),
        ("fix: move it\n\nBREAKING-CHANGE: consumers must update.", Bump.MAJOR),
    ],
)
def test_a_conventional_subject_maps_to_a_bump(message, expected):
    assert bump_for([message]) is expected


def test_the_highest_bump_in_the_set_wins():
    assert bump_for(["fix: one", "feat: two", "chore: three"]) is Bump.MINOR


def test_an_empty_set_of_commits_raises():
    with pytest.raises(NoCommitsSinceLastRelease):
        bump_for([])


def test_the_first_release_is_one_point_zero_point_zero():
    assert next_version(None, ["fix: anything"]) == Version(1, 0, 0)


def test_a_later_release_bumps_the_last_tag():
    assert next_version(Version(1, 4, 0), ["feat: more"]) == Version(1, 5, 0)


def test_a_later_release_still_needs_commits():
    with pytest.raises(NoCommitsSinceLastRelease):
        next_version(Version(1, 4, 0), [])
