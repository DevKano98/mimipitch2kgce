import re, shutil
from pathlib import Path
from app.core.errors import AppError

VALID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class LocalAssetStore:
    def __init__(self, root: Path):
        self.root = root

    def _path(self, project_id, file_id):
        if not VALID.fullmatch(project_id):
            raise AppError("invalid", "Invalid project id.", 422)
        if not VALID.fullmatch(file_id):
            raise AppError("invalid", "Invalid image file id.", 422)
        return self.root / project_id / file_id

    def save(self, project_id, file_id, mime, data):
        path = self._path(project_id, file_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        path.with_suffix(path.suffix + ".mime").write_text(mime, encoding="utf-8")

    def load(self, project_id, file_id):
        path = self._path(project_id, file_id)
        if not path.exists():
            return None
        meta = path.with_suffix(path.suffix + ".mime")
        return path.read_bytes(), meta.read_text(
            encoding="utf-8"
        ) if meta.exists() else "application/octet-stream"

    def delete_project(self, project_id):
        if not VALID.fullmatch(project_id):
            raise AppError("invalid", "Invalid project id.", 422)
        target = self.root / project_id
        if target.exists() and target.parent.resolve() == self.root.resolve():
            shutil.rmtree(target)
