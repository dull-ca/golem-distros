import shlex
import shutil
import sys
from pathlib import Path

from rich.console import Console
from rich.text import Text
from rich.tree import Tree

ROOT = Path(__file__).resolve().parent.parent.parent
NIX_STORE_PREFIX = "/nix/store/"
VIRT_CUSTOMIZE = "virt-customize"
RCLONE = "rclone"
COPYTO = "copyto"
LIVE_FLAG = "--live"
DEFAULT_WIDTH = 200

DOWNLOAD = "download"
DISK = "disk"
GUEST = "guest"
FILE = "file"
UPLOAD = "upload"

CATEGORY_STYLES = {
    DOWNLOAD: "bold cyan",
    DISK: "bold magenta",
    GUEST: "bold green",
    FILE: "bold yellow",
    UPLOAD: "bold blue",
}

CATEGORY_ICONS = {
    DOWNLOAD: "📥",
    DISK: "💽",
    GUEST: "📦",
    FILE: "📄",
    UPLOAD: "📤",
}

COMMAND_CATEGORIES = {
    "curl": DOWNLOAD,
    "qemu-img": DISK,
    "virt-resize": DISK,
    VIRT_CUSTOMIZE: GUEST,
    "mkdir": FILE,
    "mv": FILE,
    "rm": FILE,
    "chmod": FILE,
    RCLONE: UPLOAD,
}


def terminal_width() -> int:
    if not sys.stdout.isatty():
        return DEFAULT_WIDTH
    return shutil.get_terminal_size(fallback=(0, 0)).columns or DEFAULT_WIDTH


def categorize(argv: list[str]) -> str:
    return COMMAND_CATEGORIES.get(argv[0], FILE)


def shorten(token: str) -> str:
    if not token.startswith("/"):
        return token
    path = Path(token)
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        pass
    if token.startswith(NIX_STORE_PREFIX):
        return path.name
    return token


def customize_steps(arguments: list[str]) -> list[tuple[str, str]]:
    steps = []
    for index in range(0, len(arguments), 2):
        option, value = arguments[index], arguments[index + 1]
        if option == "--run":
            steps.append(("run", shorten(value)))
        elif option == "--mkdir":
            steps.append(("mkdir", value))
        elif option == "--copy-in":
            source, _, destination = value.partition(":")
            steps.append(("copy", f"{Path(source).name} → {destination}"))
        elif option == "--chown":
            uid, gid, path = value.split(":", 2)
            steps.append(("chown", f"{uid}:{gid} {path}"))
        elif option == "--chmod":
            mode, _, path = value.partition(":")
            steps.append(("chmod", f"{mode} {path}"))
    return steps


def heading(icon: str, category: str, style: str) -> Text:
    text = Text()
    text.append(f"{icon}  ")
    text.append(f"{category:<8}", style=style)
    return text


def customize_tree(argv: list[str], category: str, icon: str, style: str) -> Tree:
    header = heading(icon, category, style)
    header.append(f"{VIRT_CUSTOMIZE} -a {shorten(argv[2])}")
    tree = Tree(header)
    for label, value in customize_steps(argv[3:]):
        tree.add(f"{label:<5} {value}")
    return tree


def upload_tree(argv: list[str], category: str, icon: str, style: str) -> Tree:
    header = heading(icon, category, style)
    header.append(f"{RCLONE} {COPYTO}")
    tree = Tree(header)
    source, destination, *flags = argv[2:]
    tree.add(f"{'source':<11} {shorten(source)}")
    tree.add(f"{'destination':<11} {destination}")
    tree.add(f"{'flags':<11} {' '.join(flags)}")
    return tree


def render(argv: list[str], console: Console) -> None:
    category = categorize(argv)
    icon = CATEGORY_ICONS[category]
    style = CATEGORY_STYLES[category]
    if argv[0] == VIRT_CUSTOMIZE:
        console.print(customize_tree(argv, category, icon, style))
        return
    if argv[0] == RCLONE and len(argv) > 1 and argv[1] == COPYTO:
        console.print(upload_tree(argv, category, icon, style))
        return
    line = heading(icon, category, style)
    line.append(shlex.join(shorten(token) for token in argv))
    console.print(line, soft_wrap=True)


def make_console() -> Console:
    return Console(width=terminal_width())


def announce(argv: list[str], console: Console | None = None, live: bool = False) -> None:
    console = console or make_console()
    if live:
        console.rule(style="dim")
    render(argv, console)


def main() -> None:
    argv = sys.argv[1:]
    live = bool(argv) and argv[0] == LIVE_FLAG
    announce(argv[1:] if live else argv, live=live)


if __name__ == "__main__":
    main()
