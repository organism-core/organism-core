from pathlib import Path

import pytest

from organism.memory import ENTITY_PROFILE_FILENAME_stbr, Entity, EntityStore


def test_list_empty_root(tmp_path: Path):
    store = EntityStore(tmp_path)
    assert store.list() == []


def test_list_missing_root(tmp_path: Path):
    store = EntityStore(tmp_path / "does-not-exist")
    assert store.list() == []


def test_write_creates_directory_and_file(tmp_path: Path):
    store = EntityStore(tmp_path)
    store.write("alpha", Entity(frontmatter={"name": "alpha"}, body="hello"))
    assert (tmp_path / "alpha" / ENTITY_PROFILE_FILENAME_stbr).exists()


def test_read_round_trip(tmp_path: Path):
    store = EntityStore(tmp_path)
    original = Entity(
        frontmatter={"id": "001", "tags": ["a", "b"]},
        body="# Title\n\nbody text",
    )
    store.write("001", original)
    loaded = store.read("001")
    assert loaded.frontmatter == original.frontmatter
    assert loaded.body == original.body


def test_list_returns_sorted_ids(tmp_path: Path):
    store = EntityStore(tmp_path)
    for entity_id in ["zeta", "alpha", "mike"]:
        store.write(entity_id, Entity(body=entity_id))
    assert store.list() == ["alpha", "mike", "zeta"]


def test_list_ignores_dirs_without_entity_profile(tmp_path: Path):
    store = EntityStore(tmp_path)
    (tmp_path / "no-profile").mkdir()
    (tmp_path / "no-profile" / "other.txt").write_text("x")
    store.write("with-profile", Entity(body="x"))
    assert store.list() == ["with-profile"]


def test_list_ignores_files_at_root(tmp_path: Path):
    store = EntityStore(tmp_path)
    (tmp_path / "stray.txt").write_text("ignored")
    store.write("real", Entity(body="x"))
    assert store.list() == ["real"]


def test_exists(tmp_path: Path):
    store = EntityStore(tmp_path)
    assert not store.exists("ghost")
    store.write("real", Entity(body="x"))
    assert store.exists("real")
    assert not store.exists("ghost")


def test_write_overwrites_existing(tmp_path: Path):
    store = EntityStore(tmp_path)
    store.write("x", Entity(frontmatter={"v": 1}, body="first"))
    store.write("x", Entity(frontmatter={"v": 2}, body="second"))
    loaded = store.read("x")
    assert loaded.frontmatter == {"v": 2}
    assert loaded.body == "second"


def test_read_missing_raises(tmp_path: Path):
    store = EntityStore(tmp_path)
    with pytest.raises(FileNotFoundError):
        store.read("ghost")
