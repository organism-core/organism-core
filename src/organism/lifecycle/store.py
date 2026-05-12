from __future__ import annotations

from pathlib import Path

import yaml

from organism.lifecycle.types import LifecycleState

LIFECYCLE_FILE_SUFFIX = ".yaml"


class LifecycleStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    def write(self, state: LifecycleState) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path_for(state.kind)
        path.write_text(
            yaml.safe_dump(
                state.to_dict(),
                sort_keys=False,
                allow_unicode=True,
                default_flow_style=False,
            ),
            encoding="utf-8",
        )

    def read(self, kind: str) -> LifecycleState:
        path = self._path_for(kind)
        if not path.exists():
            raise FileNotFoundError(
                f"Lifecycle state for kind {kind!r} not found"
            )
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return LifecycleState.from_dict(data)

    def exists(self, kind: str) -> bool:
        return self._path_for(kind).exists()

    def list_kinds(self) -> list[str]:
        if not self.root.exists():
            return []
        return sorted(
            p.stem
            for p in self.root.glob(f"*{LIFECYCLE_FILE_SUFFIX}")
            if p.is_file()
        )

    def _path_for(self, kind: str) -> Path:
        return self.root / f"{kind}{LIFECYCLE_FILE_SUFFIX}"
