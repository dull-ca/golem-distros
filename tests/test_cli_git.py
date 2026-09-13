import subprocess
from pathlib import Path

import pytest

from golem_distros.cli.execution import Subprocess
from golem_distros.cli.git import Git, repository_state


def run_git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *arguments], check=True, capture_output=True, text=True
    ).stdout


def commit(root: Path, name: str, message: str) -> None:
    (root / name).write_text(name)
    run_git(root, "add", name)
    run_git(root, "commit", "-q", "-m", message)


@pytest.fixture
def git(tmp_path: Path) -> Git:
    run_git(tmp_path, "init", "-q")
    run_git(tmp_path, "config", "user.email", "release@example.com")
    run_git(tmp_path, "config", "user.name", "Release Bot")
    return Git(Subprocess(), str(tmp_path))


def root_of(git: Git) -> Path:
    return Path(git.root)


def test_messages_since_splits_distinct_commits_and_keeps_each_body(git: Git):
    commit(root_of(git), "a.txt", "feat: add a thing")
    commit(root_of(git), "b.txt", "feat: add another\n\nwith a body line")
    assert git.messages_since(None) == (
        "feat: add another\n\nwith a body line",
        "feat: add a thing",
    )


def test_messages_since_a_tag_excludes_earlier_commits(git: Git):
    commit(root_of(git), "a.txt", "feat: add a thing")
    run_git(root_of(git), "tag", "v1.0.0")
    commit(root_of(git), "b.txt", "fix: patch a thing")
    assert git.messages_since("v1.0.0") == ("fix: patch a thing",)
    assert git.messages_since("HEAD") == ()


def test_tags_lists_only_version_tags_and_the_last_is_the_highest(git: Git):
    commit(root_of(git), "a.txt", "feat: add a thing")
    for name in ("v1.0.0", "v1.4.0", "v1.2.0", "not-a-version"):
        run_git(root_of(git), "tag", name)
    assert git.tags() == frozenset({"v1.0.0", "v1.2.0", "v1.4.0"})
    assert git.last_version_tag() == "v1.4.0"


def test_head_is_the_current_commit_and_there_is_no_tag_before_the_first_release(
    git: Git,
):
    commit(root_of(git), "a.txt", "feat: add a thing")
    assert git.last_version_tag() is None
    assert git.head() == run_git(root_of(git), "rev-parse", "HEAD").strip()


def test_add_commit_and_tag_operate_on_the_real_repository(git: Git):
    commit(root_of(git), "a.txt", "feat: add a thing")
    (root_of(git) / "releases").mkdir()
    (root_of(git) / "releases" / "v1.0.0.json").write_text("{}")
    git.add(["releases"])
    git.commit("chore(release): v1.0.0")
    git.tag("v1.0.0")
    assert git.tags() == {"v1.0.0"}
    assert git.status_lines() == ()


def test_the_repository_state_reads_a_clean_tree_at_its_last_tag(git: Git):
    commit(root_of(git), "a.txt", "feat: add a thing")
    run_git(root_of(git), "tag", "v1.0.0")
    commit(root_of(git), "b.txt", "fix: patch a thing")
    state = repository_state(git)
    assert state.dirty is False
    assert state.last_tag == "v1.0.0"
    assert state.messages == ("fix: patch a thing",)
    assert state.tags == frozenset({"v1.0.0"})
    assert state.head == git.head()


def test_the_repository_state_is_dirty_and_names_an_untracked_file(git: Git):
    commit(root_of(git), "a.txt", "feat: add a thing")
    (root_of(git) / "untracked.txt").write_text("noise")
    state = repository_state(git)
    assert state.dirty is True
    assert len(state.status) == 1
    assert "untracked.txt" in state.status[0]
