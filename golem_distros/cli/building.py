from dataclasses import dataclass
from pathlib import Path

from golem_distros.cli.workspace import Workspace
from golem_distros.model import GOLEMD_SOURCE, Distro, Payload
from golem_distros.ports import Files, Runner

BUILD_SCRIPT = str(Path(__file__).resolve().parent.parent.parent / "image" / "build.sh")
RUN_ACTION = "run"
COPY_ACTION = "copy"
NO_MODE = "-"
DRY_RUN_OPTION = "--dry-run"


@dataclass(frozen=True)
class BuiltImage:
    distro_name: str
    path: str
    sha512: str


def image_path(workspace: Workspace, distro: Distro) -> str:
    return f"{workspace.output}/{distro.name}.qcow2"


def copy_action(payload: Payload, golemd: str) -> tuple[str, ...]:
    source = golemd if payload.source == GOLEMD_SOURCE else payload.source
    return (COPY_ACTION, source, payload.destination, payload.mode or NO_MODE)


def build_actions(distro: Distro, golemd: str) -> tuple[str, ...]:
    actions: tuple[str, ...] = ()
    for step in distro.steps:
        for payload in step.payloads:
            actions += copy_action(payload, golemd)
        actions += (RUN_ACTION, step.script)
    for payload in distro.payloads:
        actions += copy_action(payload, golemd)
    return actions


def build_command(
    distro: Distro, workspace: Workspace, golemd: str, dry_run: bool = False
) -> tuple[str, ...]:
    return (
        BUILD_SCRIPT,
        *((DRY_RUN_OPTION,) if dry_run else ()),
        distro.name,
        distro.base.url,
        distro.base.sha512,
        distro.size,
        distro.root_partition,
        workspace.output,
        *build_actions(distro, golemd),
    )


def build_image(
    distro: Distro,
    workspace: Workspace,
    golemd: str,
    runner: Runner,
    files: Files,
) -> BuiltImage:
    path = image_path(workspace, distro)
    runner.run(build_command(distro, workspace, golemd))
    return BuiltImage(distro_name=distro.name, path=path, sha512=files.sha512(path))
