from __future__ import annotations

from pathlib import Path

import yaml

from organism.plan_gate.types import Plan, PlanStatus

PLAN_FILE_SUFFIX = ".yaml"


class PlanStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    def write(self, plan: Plan) -> None:
        path = self.root / plan.kind / f"{plan.id}{PLAN_FILE_SUFFIX}"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.safe_dump(
                plan.to_dict(),
                sort_keys=False,
                allow_unicode=True,
                default_flow_style=False,
            ),
            encoding="utf-8",
        )

    def read(self, plan_id: str) -> Plan:
        path = self._find_path(plan_id)
        if path is None:
            raise FileNotFoundError(f"Plan {plan_id!r} not found")
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return Plan.from_dict(data)

    def exists(self, plan_id: str) -> bool:
        return self._find_path(plan_id) is not None

    def list(
        self,
        kind: str | None = None,
        status: PlanStatus | None = None,
    ) -> list[Plan]:
        if not self.root.exists():
            return []
        plans: list[Plan] = []
        kind_dirs = self._kind_dirs(kind)
        for kind_dir in kind_dirs:
            for plan_file in sorted(kind_dir.glob(f"*{PLAN_FILE_SUFFIX}")):
                data = yaml.safe_load(plan_file.read_text(encoding="utf-8"))
                plan = Plan.from_dict(data)
                if status is not None and plan.status != status:
                    continue
                plans.append(plan)
        return plans

    def _kind_dirs(self, kind: str | None) -> list[Path]:
        if kind is not None:
            target = self.root / kind
            return [target] if target.is_dir() else []
        return sorted(p for p in self.root.iterdir() if p.is_dir())

    def _find_path(self, plan_id: str) -> Path | None:
        if not self.root.exists():
            return None
        for kind_dir in self.root.iterdir():
            if not kind_dir.is_dir():
                continue
            candidate = kind_dir / f"{plan_id}{PLAN_FILE_SUFFIX}"
            if candidate.exists():
                return candidate
        return None
