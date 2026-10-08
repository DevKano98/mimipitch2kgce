import json, sqlite3, uuid
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


class SQLiteRepository:
    def __init__(self, path: Path):
        self.path = path

    def _db(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=WAL")
        return db

    def init(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._db() as db:
            db.executescript(
                """CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,owner_id TEXT,title TEXT,created_at TEXT,updated_at TEXT);CREATE TABLE IF NOT EXISTS canvases(project_id TEXT PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,scene_json TEXT,version INTEGER,updated_at TEXT);CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY,project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,role TEXT,content TEXT,metadata_json TEXT,created_at TEXT);CREATE TABLE IF NOT EXISTS ai_actions(id TEXT PRIMARY KEY,project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,message_id TEXT,mode TEXT,actions_json TEXT,created_at TEXT);CREATE TABLE IF NOT EXISTS lesson_state(project_id TEXT PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,state_json TEXT,updated_at TEXT);CREATE INDEX IF NOT EXISTS projects_owner_updated ON projects(owner_id,updated_at);CREATE INDEX IF NOT EXISTS messages_project_created ON messages(project_id,created_at);"""
            )

    def list_projects(self, owner):
        with self._db() as db:
            return [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM projects WHERE owner_id=? ORDER BY updated_at DESC",
                    (owner,),
                )
            ]

    def create_project(self, owner, title):
        ident = str(uuid.uuid4())
        stamp = now()
        with self._db() as db:
            db.execute(
                "INSERT INTO projects VALUES(?,?,?,?,?)",
                (ident, owner, title, stamp, stamp),
            )
        return self.get_project(owner, ident)

    def get_project(self, owner, ident):
        with self._db() as db:
            row = db.execute(
                "SELECT * FROM projects WHERE owner_id=? AND id=?", (owner, ident)
            ).fetchone()
            return dict(row) if row else None

    def rename_project(self, owner, ident, title):
        with self._db() as db:
            db.execute(
                "UPDATE projects SET title=?,updated_at=? WHERE owner_id=? AND id=?",
                (title, now(), owner, ident),
            )
        return self.get_project(owner, ident)

    def delete_project(self, owner, ident):
        with self._db() as db:
            return (
                db.execute(
                    "DELETE FROM projects WHERE owner_id=? AND id=?", (owner, ident)
                ).rowcount
                > 0
            )

    def load_scene(self, ident):
        with self._db() as db:
            row = db.execute(
                "SELECT scene_json FROM canvases WHERE project_id=?", (ident,)
            ).fetchone()
            return json.loads(row[0]) if row else None

    def save_scene(self, ident, scene):
        stamp = now()
        with self._db() as db:
            db.execute(
                "INSERT INTO canvases VALUES(?,?,1,?) ON CONFLICT(project_id) DO UPDATE SET scene_json=excluded.scene_json,version=canvases.version+1,updated_at=excluded.updated_at",
                (ident, json.dumps(scene, separators=(",", ":")), stamp),
            )
            db.execute("UPDATE projects SET updated_at=? WHERE id=?", (stamp, ident))
        return stamp

    def add_message(self, project_id, role, content, metadata):
        ident = str(uuid.uuid4())
        with self._db() as db:
            db.execute(
                "INSERT INTO messages VALUES(?,?,?,?,?,?)",
                (ident, project_id, role, content, json.dumps(metadata), now()),
            )
        return ident

    def list_messages(self, project_id, limit=50):
        with self._db() as db:
            return [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM messages WHERE project_id=? ORDER BY created_at DESC LIMIT ?",
                    (project_id, min(limit, 50)),
                )
            ]

    def add_ai_action(self, project_id, message_id, mode, actions):
        ident = str(uuid.uuid4())
        with self._db() as db:
            db.execute(
                "INSERT INTO ai_actions VALUES(?,?,?,?,?,?)",
                (ident, project_id, message_id, mode, json.dumps(actions), now()),
            )
        return ident

    def get_lesson_state(self, project_id):
        with self._db() as db:
            row = db.execute(
                "SELECT state_json FROM lesson_state WHERE project_id=?", (project_id,)
            ).fetchone()
            return json.loads(row[0]) if row else None

    def set_lesson_state(self, project_id, state):
        with self._db() as db:
            db.execute(
                "INSERT INTO lesson_state VALUES(?,?,?) ON CONFLICT(project_id) DO UPDATE SET state_json=excluded.state_json,updated_at=excluded.updated_at",
                (project_id, json.dumps(state)[:2048], now()),
            )
