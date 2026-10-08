import base64, re
from fastapi import APIRouter, Depends, Response
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.dependencies import get_assets, get_repo
from app.schemas.project import CanvasLoad, CanvasSave, ProjectCreate, ProjectRename

router = APIRouter()
MAX_IMAGE_BYTES = 5_500_000


def decode_image_data_url(value: str) -> tuple[str, bytes]:
    match = re.fullmatch(r"data:(image/[A-Za-z0-9.+-]+);base64,(.+)", value, re.S)
    if not match:
        raise AppError("invalid", "Invalid image data.", 422)
    try:
        raw = base64.b64decode(match.group(2), validate=True)
    except Exception as exc:
        raise AppError("invalid", "Invalid image data.", 422) from exc
    if len(raw) > MAX_IMAGE_BYTES:
        raise AppError("invalid", "An image is too large. Resize it below 5 MB.", 413)
    return match.group(1), raw


def ensure(repo, s, ident):
    p = repo.get_project(s.local_user_id, ident)
    if not p:
        raise AppError("not_found", "Project not found.", 404)
    return p


@router.get("/projects")
def projects(
    repo=Depends(get_repo),
    assets=Depends(get_assets),
    s: Settings = Depends(get_settings),
):
    return [
        {**p, "has_thumbnail": bool(assets.load(p["id"], "thumbnail"))}
        for p in repo.list_projects(s.local_user_id)
    ]


@router.post("/projects", status_code=201)
def create(
    body: ProjectCreate, repo=Depends(get_repo), s: Settings = Depends(get_settings)
):
    return {
        **repo.create_project(s.local_user_id, body.title.strip()),
        "has_thumbnail": False,
    }


@router.get("/projects/{ident}")
def get_project(
    ident: str,
    repo=Depends(get_repo),
    assets=Depends(get_assets),
    s: Settings = Depends(get_settings),
):
    p = ensure(repo, s, ident)
    return {**p, "has_thumbnail": bool(assets.load(ident, "thumbnail"))}


@router.patch("/projects/{ident}")
def rename(
    ident: str,
    body: ProjectRename,
    repo=Depends(get_repo),
    assets=Depends(get_assets),
    s: Settings = Depends(get_settings),
):
    ensure(repo, s, ident)
    return {
        **repo.rename_project(s.local_user_id, ident, body.title.strip()),
        "has_thumbnail": bool(assets.load(ident, "thumbnail")),
    }


@router.delete("/projects/{ident}", status_code=204)
def delete(
    ident: str,
    repo=Depends(get_repo),
    assets=Depends(get_assets),
    s: Settings = Depends(get_settings),
):
    if not repo.delete_project(s.local_user_id, ident):
        raise AppError("not_found", "Project not found.", 404)
    assets.delete_project(ident)
    return Response(status_code=204)


@router.put("/projects/{ident}/canvas")
def save_canvas(
    ident: str,
    body: CanvasSave,
    repo=Depends(get_repo),
    assets=Depends(get_assets),
    s: Settings = Depends(get_settings),
):
    ensure(repo, s, ident)
    stored = {}
    for file_id, meta in body.files.items():
        clean = dict(meta)
        data_url = clean.pop("dataURL", None)
        if data_url:
            mime, raw = decode_image_data_url(data_url)
            assets.save(ident, file_id, mime, raw)
        stored[file_id] = clean
    if body.thumbnail_data_url:
        mime, raw = decode_image_data_url(body.thumbnail_data_url)
        assets.save(ident, "thumbnail", mime, raw)
    return {
        "updated_at": repo.save_scene(
            ident,
            {"elements": body.elements, "app_state": body.app_state, "files": stored},
        )
    }


@router.get("/projects/{ident}/canvas", response_model=CanvasLoad)
def load_canvas(
    ident: str,
    repo=Depends(get_repo),
    assets=Depends(get_assets),
    s: Settings = Depends(get_settings),
):
    ensure(repo, s, ident)
    scene = repo.load_scene(ident) or {"elements": [], "app_state": {}, "files": {}}
    for file_id, meta in scene["files"].items():
        saved = assets.load(ident, file_id)
        if saved:
            meta["dataURL"] = (
                f"data:{saved[1]};base64,{base64.b64encode(saved[0]).decode()}"
            )
    return scene


@router.get("/projects/{ident}/thumbnail")
def thumbnail(ident: str, assets=Depends(get_assets)):
    saved = assets.load(ident, "thumbnail")
    if not saved:
        raise AppError("not_found", "Thumbnail not found.", 404)
    return Response(saved[0], media_type=saved[1])


@router.get("/projects/{ident}/messages")
def messages(ident: str, repo=Depends(get_repo)):
    return repo.list_messages(ident)
