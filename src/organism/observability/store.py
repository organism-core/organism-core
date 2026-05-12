from __future__ import annotations

from pathlib import Path

import yaml

from organism.observability.trace import Trace
from organism.orchestrator.types import ActionStatus

TRACE_FILE_SUFFIX = ".yaml"


class TraceStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    def write(self, trace: Trace) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path_for(trace.id)
        path.write_text(
            yaml.safe_dump(
                trace.to_dict(),
                sort_keys=False,
                allow_unicode=True,
                default_flow_style=False,
            ),
            encoding="utf-8",
        )

    def read(self, trace_id: str) -> Trace:
        path = self._path_for(trace_id)
        if not path.exists():
            raise FileNotFoundError(f"Trace {trace_id!r} not found")
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return Trace.from_dict(data)

    def exists(self, trace_id: str) -> bool:
        return self._path_for(trace_id).exists()

    def list(
        self,
        kind: str | None = None,
        status: ActionStatus | None = None,
    ) -> list[Trace]:
        if not self.root.exists():
            return []
        traces: list[Trace] = []
        for path in sorted(self.root.glob(f"*{TRACE_FILE_SUFFIX}")):
            if not path.is_file():
                continue
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            trace = Trace.from_dict(data)
            if kind is not None and trace.kind != kind:
                continue
            if status is not None and trace.status != status:
                continue
            traces.append(trace)
        return traces

    def _path_for(self, trace_id: str) -> Path:
        return self.root / f"{trace_id}{TRACE_FILE_SUFFIX}"
