from dataclasses import dataclass
from pathlib import Path

OUTPUT_DIRECTORY = "output"


@dataclass(frozen=True)
class Workspace:
    root: str
    output: str

    @classmethod
    def discover(cls) -> "Workspace":
        root = Path(__file__).resolve().parent.parent.parent
        return cls(root=str(root), output=str(root / OUTPUT_DIRECTORY))
