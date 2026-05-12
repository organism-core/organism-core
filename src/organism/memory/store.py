from __future__ import annotations

from pathlib import Path

from organism.memory.entity import Entity, dump, parse

# On-disk filename for an entity's profile. The ``_stbr`` consonant-
# suffix on the identifier is a documented convention — see
# docs/TRANSLATION_GUIDE.md.
ENTITY_PROFILE_FILENAME_stbr = "_entity_profile.md"


class EntityStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    def list(self) -> list[str]:
        if not self.root.exists():
            return []
        return sorted(
            p.name
            for p in self.root.iterdir()
            if p.is_dir() and (p / ENTITY_PROFILE_FILENAME_stbr).exists()
        )

    def exists(self, entity_id: str) -> bool:
        return (self.root / entity_id / ENTITY_PROFILE_FILENAME_stbr).exists()

    def read(self, entity_id: str) -> Entity:
        path = self.root / entity_id / ENTITY_PROFILE_FILENAME_stbr
        return parse(path.read_text(encoding="utf-8"))

    def write(self, entity_id: str, entity: Entity) -> None:
        dir_path = self.root / entity_id
        dir_path.mkdir(parents=True, exist_ok=True)
        (dir_path / ENTITY_PROFILE_FILENAME_stbr).write_text(
            dump(entity), encoding="utf-8"
        )
