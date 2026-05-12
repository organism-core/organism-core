from __future__ import annotations

from pathlib import Path

import yaml

from organism.lessons.types import Lesson

LESSON_FILE_SUFFIX = ".yaml"


class LessonsStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    def write(self, lesson: Lesson) -> None:
        path = self.root / lesson.kind / f"{lesson.id}{LESSON_FILE_SUFFIX}"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.safe_dump(
                lesson.to_dict(),
                sort_keys=False,
                allow_unicode=True,
                default_flow_style=False,
            ),
            encoding="utf-8",
        )

    def read(self, lesson_id: str) -> Lesson:
        path = self._find_path(lesson_id)
        if path is None:
            raise FileNotFoundError(f"Lesson {lesson_id!r} not found")
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return Lesson.from_dict(data)

    def exists(self, lesson_id: str) -> bool:
        return self._find_path(lesson_id) is not None

    def list(self, kind: str | None = None) -> list[Lesson]:
        if not self.root.exists():
            return []
        lessons: list[Lesson] = []
        kind_dirs = self._kind_dirs(kind)
        for kind_dir in kind_dirs:
            for path in sorted(kind_dir.glob(f"*{LESSON_FILE_SUFFIX}")):
                data = yaml.safe_load(path.read_text(encoding="utf-8"))
                lessons.append(Lesson.from_dict(data))
        return lessons

    def _kind_dirs(self, kind: str | None) -> list[Path]:
        if kind is not None:
            target = self.root / kind
            return [target] if target.is_dir() else []
        return sorted(p for p in self.root.iterdir() if p.is_dir())

    def _find_path(self, lesson_id: str) -> Path | None:
        if not self.root.exists():
            return None
        for kind_dir in self.root.iterdir():
            if not kind_dir.is_dir():
                continue
            candidate = kind_dir / f"{lesson_id}{LESSON_FILE_SUFFIX}"
            if candidate.exists():
                return candidate
        return None
