import asyncio
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from app.core.errors import AppError
from app.core.config import get_settings
from app.dependencies import get_orchestrator, get_repo
from app.schemas.ai import AskRequest

router = APIRouter()


async def run_and_persist(req, orchestrator, repo, send):
    if not repo.get_project(get_settings().local_user_id, req.project_id):
        raise AppError("not_found", "Project not found.", 404)
    events = []

    async def emit(event):
        events.append(event)
        await send(event)

    rows = list(reversed(repo.list_messages(req.project_id, 6)))
    history = [{"role": row["role"], "content": row["content"]} for row in rows]
    await orchestrator.run(
        req, emit, history=history, lesson_state=repo.get_lesson_state(req.project_id)
    )
    done = next((e for e in reversed(events) if e["type"] == "done"), None)
    if done:
        repo.add_message(req.project_id, "user", req.prompt, {"mode": req.mode})
        message_id = repo.add_message(req.project_id, "assistant", done["text"], {})
        repo.add_ai_action(
            req.project_id,
            message_id,
            req.mode,
            [e["step"] for e in events if e["type"] == "step"],
        )
        if done.get("lesson_state"):
            repo.set_lesson_state(req.project_id, done["lesson_state"])
    return events


@router.post("/ai/ask")
async def ask(
    req: AskRequest, orchestrator=Depends(get_orchestrator), repo=Depends(get_repo)
):
    events = []

    async def collect(event):
        events.append(event)

    await run_and_persist(req, orchestrator, repo, collect)
    return {"events": events}


async def ai_socket(websocket: WebSocket):
    await websocket.accept()
    orchestrator = get_orchestrator()
    repo = get_repo()
    task = None
    try:
        while True:
            message = await websocket.receive_json()
            if message.get("type") == "cancel":
                if task and not task.done():
                    task.cancel()
                continue
            if message.get("type") != "ask":
                continue
            if task and not task.done():
                task.cancel()
            try:
                req = AskRequest.model_validate(message.get("payload"))
            except Exception:
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "invalid",
                        "message": "The request was invalid. Try selecting the problem again.",
                    }
                )
                continue

            async def send(event):
                await websocket.send_json(event)

            async def work():
                try:
                    await run_and_persist(req, orchestrator, repo, send)
                except asyncio.CancelledError:
                    return
                except AppError as exc:
                    await send(
                        {"type": "error", "code": exc.code, "message": exc.message}
                    )
                except Exception:
                    await send(
                        {
                            "type": "error",
                            "code": "model_error",
                            "message": "The AI request failed. Try again.",
                        }
                    )

            task = asyncio.create_task(work())
    except WebSocketDisconnect:
        if task and not task.done():
            task.cancel()
