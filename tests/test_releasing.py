import pytest

from golem_distros.releasing import (
    DirtyWorkingTree,
    RepositoryState,
    TagAlreadyExists,
    plan_release,
)
from semver import Version

from golem_distros.versioning import NoCommitsSinceLastRelease


def a_state(**changes) -> RepositoryState:
    values = {
        "dirty": False,
        "last_tag": "v1.3.0",
        "messages": ("feat: add a thing",),
        "tags": frozenset({"v1.0.0", "v1.3.0"}),
        "head": "8f2c1ab",
        "status": (),
    }
    values.update(changes)
    return RepositoryState(**values)


def test_a_clean_tree_with_a_feature_gives_the_next_minor():
    assert plan_release(a_state()) == Version(1, 4, 0)


def test_a_dirty_tree_stops_the_release():
    with pytest.raises(DirtyWorkingTree):
        plan_release(a_state(dirty=True))


def test_no_commits_since_the_tag_stops_the_release():
    with pytest.raises(NoCommitsSinceLastRelease):
        plan_release(a_state(messages=()))


def test_an_existing_target_tag_stops_the_release():
    with pytest.raises(TagAlreadyExists):
        plan_release(a_state(tags=frozenset({"v1.3.0", "v1.4.0"})))


def test_the_dirty_check_runs_before_the_commit_check():
    with pytest.raises(DirtyWorkingTree):
        plan_release(a_state(dirty=True, messages=()))


def test_a_dirty_tree_names_the_offending_paths():
    with pytest.raises(DirtyWorkingTree, match="releases/v1.3.0.json"):
        plan_release(a_state(dirty=True, status=("?? releases/v1.3.0.json",)))
