import pytest

from golem_distros import distros
from golem_distros.cli.building import BUILD_SCRIPT
from golem_distros.cli.releasing import run_release
from golem_distros.ports import CommandFailed
from golem_distros.releasing import RepositoryState
from tests.doubles import DESTINATION, WORKSPACE, FakeFiles, RecordingRunner

STATE = RepositoryState(
    dirty=False,
    last_tag="v1.3.0",
    messages=("feat: add a thing",),
    tags=frozenset({"v1.3.0"}),
    head="8f2c1ab",
)
LOCKED = {"owner": "dull-ca", "repo": "golem", "rev": "41bf030", "type": "github"}
LOCK = {"nodes": {"golem": {"locked": LOCKED}}}


class RecordingGit:
    def __init__(self) -> None:
        self.added: list[tuple[str, ...]] = []
        self.commits: list[str] = []
        self.tags: list[str] = []

    def add(self, paths):
        self.added.append(tuple(paths))

    def commit(self, message):
        self.commits.append(message)

    def tag(self, name):
        self.tags.append(name)


def a_run(git: RecordingGit, files: FakeFiles, runner: RecordingRunner):
    return run_release(
        state=STATE,
        workspace=WORKSPACE,
        destination=DESTINATION,
        golemd="/nix/store/abc/bin/golemd",
        lock=LOCK,
        released_at="2026-09-12T20:31:04Z",
        runner=runner,
        files=files,
        git=git,
    )


def files_ready() -> FakeFiles:
    digests = {
        f"{WORKSPACE.output}/{distro.name}.qcow2": chr(ord("a") + index) * 128
        for index, distro in enumerate(distros.all_distros())
    }
    return FakeFiles(present=list(digests), digests=digests)


def test_the_release_builds_every_configuration_and_records_its_provenance():
    release = a_run(RecordingGit(), files_ready(), RecordingRunner())
    assert sorted(release.images) == ["golem-do", "golem-ovh"]
    assert release.version == "v1.4.0"
    assert release.commit == "8f2c1ab"
    assert release.released == "2026-09-12T20:31:04Z"
    assert release.golemd.rev == "41bf030"
    assert release.golemd.flake == "github:dull-ca/golem"


def test_the_manifest_is_written_into_the_releases_directory():
    files = files_ready()
    a_run(RecordingGit(), files, RecordingRunner())
    assert "/repo/releases/v1.4.0.json" in files.written


def test_the_manifest_and_latest_are_both_uploaded():
    runner = RecordingRunner()
    a_run(RecordingGit(), files_ready(), runner)
    targets = [call[3] for call in runner.calls if call[0] == "rclone"]
    assert "images:golem-distros/releases/v1.4.0.json" in targets
    assert "images:golem-distros/releases/latest.json" in targets


def test_the_release_stages_only_the_releases_directory_then_commits_and_tags():
    git = RecordingGit()
    a_run(git, files_ready(), RecordingRunner())
    assert git.added == [("releases",)]
    assert git.commits[0].startswith("chore(release): v1.4.0")
    assert git.tags == ["v1.4.0"]


def test_the_release_never_pushes():
    runner = RecordingRunner()
    a_run(RecordingGit(), files_ready(), runner)
    assert all("push" not in call for call in runner.calls)


class FailingManifestRunner(RecordingRunner):
    def run(self, argv, env=None):
        super().run(argv, env)
        if argv[0] == "rclone" and argv[3].endswith("releases/v1.4.0.json"):
            raise CommandFailed("network blip")


class FailingSecondBuildRunner(RecordingRunner):
    def run(self, argv, env=None):
        if argv[0] == BUILD_SCRIPT and argv[1] == "golem-ovh":
            raise CommandFailed("build blip")
        super().run(argv, env)


def test_a_failed_second_build_uploads_nothing():
    runner = FailingSecondBuildRunner()
    with pytest.raises(CommandFailed):
        a_run(RecordingGit(), files_ready(), runner)
    assert not any(call[0] == "rclone" for call in runner.calls)


def test_a_failed_manifest_upload_leaves_the_working_tree_untouched():
    git, files = RecordingGit(), files_ready()
    with pytest.raises(CommandFailed):
        a_run(git, files, FailingManifestRunner())
    assert not any(path.startswith("/repo/releases/") for path in files.written)
    assert git.added == []
    assert git.commits == []
    assert git.tags == []
