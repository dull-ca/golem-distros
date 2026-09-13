import json
import os
from datetime import datetime, timezone
from pathlib import Path

import typer

from golem_distros import distros
from golem_distros.cli import booting, building, publishing, releasing
from golem_distros.cli.execution import DryRun, Subprocess
from golem_distros.cli.files import DryRunFiles, LocalFiles
from golem_distros.cli.git import Git, repository_state
from golem_distros.cli.workspace import Workspace
from golem_distros.model import Distro
from golem_distros.ports import CommandFailed, Files

GOLEMD_VARIABLE = "GOLEM_DISTROS_GOLEMD"
LOCKFILE = "devenv.lock"

app = typer.Typer(add_completion=False, no_args_is_help=True)


def stop(message: str, code: int = 2) -> typer.Exit:
    typer.echo(message)
    return typer.Exit(code=code)


def chosen_distro(name: str) -> Distro:
    try:
        return distros.find(name)
    except distros.UnknownDistro as unknown:
        raise stop(str(unknown))


def chosen_destination() -> publishing.Destination:
    try:
        return publishing.Destination.from_environment()
    except publishing.MissingCredentials as missing:
        raise stop(str(missing))


def required_environment(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise stop(f"{name} is not set; enter the devenv shell first")
    return value


def already_built(
    workspace: Workspace, distro: Distro, files: Files
) -> building.BuiltImage:
    path = building.image_path(workspace, distro)
    if not files.exists(path):
        raise stop(f"no image at {path}; build {distro.name} first")
    return building.BuiltImage(distro.name, path, files.sha512(path))


@app.command("list")
def list_distros() -> None:
    for name in distros.names():
        typer.echo(name)


@app.command()
def build(name: str, dry_run: bool = typer.Option(False, "--dry-run")) -> None:
    distro = chosen_distro(name)
    workspace = Workspace.discover()
    if dry_run:
        golemd = os.environ.get(GOLEMD_VARIABLE, f"${GOLEMD_VARIABLE}")
        preview = building.build_command(distro, workspace, golemd, dry_run=True)
        typer.echo(Subprocess().capture(preview))
        return
    golemd = required_environment(GOLEMD_VARIABLE)
    built = building.build_image(
        distro, workspace, golemd, Subprocess(), LocalFiles()
    )
    typer.echo(f"image    {built.path}")
    typer.echo(f"checksum {built.sha512}")


@app.command()
def boot(
    name: str,
    seed: str | None = typer.Option(None, "--seed"),
    memory: int = typer.Option(2048, "--memory"),
    direct: bool = typer.Option(False, "--direct"),
) -> None:
    distro = chosen_distro(name)
    workspace = Workspace.discover()
    files = LocalFiles()
    before = already_built(workspace, distro, files)
    typer.echo(f"image    {before.path}")
    typer.echo(f"checksum {before.sha512}")
    booting.boot_image(distro, workspace, seed, memory, Subprocess(), files, direct)
    after = files.sha512(before.path)
    typer.echo(f"checksum {after}")
    if after != before.sha512:
        raise stop("the image changed during the boot; do not publish it", code=1)


@app.command()
def publish(
    name: str,
    version: str = typer.Option(..., "--version"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    distro = chosen_distro(name)
    workspace = Workspace.discover()
    files = DryRunFiles(typer.echo) if dry_run else LocalFiles()
    built = already_built(workspace, distro, files)
    runner = DryRun(typer.echo) if dry_run else Subprocess()
    destination = (
        publishing.Destination.without_credentials()
        if dry_run
        else chosen_destination()
    )
    published = publishing.publish_image(
        built, version, destination, workspace, runner, files
    )
    typer.echo(f"url      {published.url}")
    typer.echo(f"checksum {published.sha512}")


@app.command("test-access")
def test_access() -> None:
    destination = chosen_destination()
    typer.echo(f"bucket   s3://{destination.bucket}")
    typer.echo(f"endpoint https://{destination.endpoint}")
    typer.echo(f"region   {destination.region}")
    try:
        Subprocess().run(
            publishing.access_check_command(destination.bucket),
            publishing.aws_environment(destination),
        )
    except CommandFailed:
        raise stop("the credentials cannot read that bucket", code=1)
    typer.echo("the credentials can read that bucket")


@app.command()
def release() -> None:
    workspace = Workspace.discover()
    runner = Subprocess()
    repository = Git(runner, workspace.root)
    destination = chosen_destination()
    released = releasing.run_release(
        state=repository_state(repository),
        workspace=workspace,
        destination=destination,
        golemd=required_environment(GOLEMD_VARIABLE),
        lock=json.loads(Path(f"{workspace.root}/{LOCKFILE}").read_text()),
        released_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        runner=runner,
        files=LocalFiles(),
        git=repository,
    )
    typer.echo(f"released {released.version}")
    for name, record in sorted(released.images.items()):
        typer.echo(f"{name}  {record.url}")
    typer.echo("push the tag yourself")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
