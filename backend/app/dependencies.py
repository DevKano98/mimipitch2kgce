from functools import lru_cache
from pathlib import Path
from app.ai.groq_client import GroqClient
from app.ai.orchestrator import Orchestrator
from app.ai.safety import SafetyChecker
from app.core.config import get_settings
from app.core.usage import UsageCounter
from app.services.assets import LocalAssetStore
from app.services.speech import SpeechService
from app.services.sqlite_repo import SQLiteRepository

BASE = Path(__file__).resolve().parents[1]


@lru_cache
def get_repo():
    repo = SQLiteRepository(BASE / "data" / "slate.db")
    repo.init()
    return repo


@lru_cache
def get_assets():
    return LocalAssetStore(BASE / "data" / "assets")


@lru_cache
def get_speech():
    return SpeechService(get_settings())


@lru_cache
def get_orchestrator():
    settings = get_settings()
    llm = GroqClient(settings)
    return Orchestrator(
        llm,
        SafetyChecker(settings, llm),
        settings,
        UsageCounter(settings.daily_ai_call_cap),
    )
