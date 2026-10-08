from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.ai import ai_socket, router as ai_router
from app.api.health import router as health_router
from app.api.projects import router as projects_router
from app.api.voice import router as voice_router
from app.core.config import get_settings
from app.core.errors import AppError, app_error_handler
from app.dependencies import get_repo


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_repo().init()
    yield


app = FastAPI(title="Slate API", lifespan=lifespan)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_exception_handler(AppError, app_error_handler)
for router in (health_router, projects_router, voice_router, ai_router):
    app.include_router(router, prefix="/api")
app.websocket("/ws/ai")(ai_socket)
