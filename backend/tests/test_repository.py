import base64
from pathlib import Path
import pytest
from app.core.errors import AppError
from app.services.assets import LocalAssetStore
from app.services.sqlite_repo import SQLiteRepository


def test_repository_round_trip(tmp_path: Path):
    repo = SQLiteRepository(tmp_path / "slate.db")
    repo.init()
    project = repo.create_project("owner", "Test")
    repo.save_scene(
        project["id"], {"elements": [{"id": "x"}], "app_state": {}, "files": {}}
    )
    assert repo.load_scene(project["id"])["elements"][0]["id"] == "x"
    assert repo.rename_project("owner", project["id"], "Renamed")["title"] == "Renamed"
    assert repo.delete_project("owner", project["id"])


def test_asset_ids_are_safe(tmp_path: Path):
    store = LocalAssetStore(tmp_path)
    store.save("project", "file_1", "image/png", b"png")
    assert store.load("project", "file_1")[0] == b"png"
    with pytest.raises(AppError):
        store.save("project", "../escape", "image/png", b"bad")
