import base64
from pathlib import Path
from fastapi.testclient import TestClient
from app.dependencies import get_assets, get_repo, get_speech
from app.main import app
from app.services.assets import LocalAssetStore
from app.services.sqlite_repo import SQLiteRepository


def test_project_and_canvas_api(tmp_path: Path):
    repo = SQLiteRepository(tmp_path / "db.sqlite")
    repo.init()
    assets = LocalAssetStore(tmp_path / "assets")
    app.dependency_overrides[get_repo] = lambda: repo
    app.dependency_overrides[get_assets] = lambda: assets
    try:
        with TestClient(app) as client:
            created = client.post("/api/projects", json={"title": "Physics"})
            assert created.status_code == 201
            ident = created.json()["id"]
            assert client.get("/api/projects").json()[0]["title"] == "Physics"
            assert (
                client.patch(
                    f"/api/projects/{ident}", json={"title": "Mechanics"}
                ).json()["title"]
                == "Mechanics"
            )
            data = "data:image/png;base64," + base64.b64encode(b"fake-png").decode()
            saved = client.put(
                f"/api/projects/{ident}/canvas",
                json={
                    "elements": [{"id": "image"}],
                    "app_state": {},
                    "files": {
                        "safe_id": {
                            "id": "safe_id",
                            "mimeType": "image/png",
                            "created": 1,
                            "dataURL": data,
                        }
                    },
                },
            )
            assert saved.status_code == 200
            loaded = client.get(f"/api/projects/{ident}/canvas").json()
            assert loaded["files"]["safe_id"]["dataURL"] == data
            rejected = client.put(
                f"/api/projects/{ident}/canvas",
                json={
                    "elements": [],
                    "app_state": {},
                    "files": {"../escape": {"dataURL": data}},
                },
            )
            assert (
                rejected.status_code == 422
                and rejected.json()["error"]["code"] == "invalid"
            )
            wrong_mime = (
                "data:text/html;base64," + base64.b64encode(b"<script>").decode()
            )
            rejected = client.put(
                f"/api/projects/{ident}/canvas",
                json={
                    "elements": [],
                    "app_state": {},
                    "files": {"safe": {"dataURL": wrong_mime}},
                },
            )
            assert (
                rejected.status_code == 422
                and rejected.json()["error"]["code"] == "invalid"
            )
            assert client.delete(f"/api/projects/{ident}").status_code == 204
    finally:
        app.dependency_overrides.clear()


def test_health_does_not_expose_keys():
    with TestClient(app) as client:
        body = client.get("/api/health").json()
        assert "groq_configured" in body and "groq_api_key" not in body


def test_blank_project_title_is_rejected():
    with TestClient(app) as client:
        assert client.post("/api/projects", json={"title": "   "}).status_code == 422


def test_voice_endpoints_use_backend_provider():
    class FakeSpeech:
        async def transcribe(self, data, filename, mime, language):
            assert (
                data == b"wav"
                and filename == "clip.wav"
                and mime == "audio/wav"
                and language == "hi-IN"
            )
            return {"transcript": "hello", "language_code": "hi-IN", "provider": "fake"}

        async def speak(self, text, language):
            assert text == "hello" and language == "en-IN"
            return {"audio_base64": "audio", "mime": "audio/wav"}

    app.dependency_overrides[get_speech] = FakeSpeech
    try:
        with TestClient(app) as client:
            transcript = client.post(
                "/api/transcribe",
                files={"file": ("clip.wav", b"wav", "audio/wav")},
                data={"language": "hi-IN"},
            )
            assert (
                transcript.status_code == 200
                and transcript.json()["transcript"] == "hello"
            )
            audio = client.post(
                "/api/speak", json={"text": "hello", "language_code": "en-IN"}
            )
            assert audio.status_code == 200 and audio.json()["mime"] == "audio/wav"
    finally:
        app.dependency_overrides.clear()
