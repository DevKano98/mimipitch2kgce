from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    groq_api_key: str = ""
    sarvam_api_key: str = ""
    groq_vision_model: str = "qwen/qwen3.8-27b"
    groq_safety_model: str = "openai/gpt-oss-safeguard-20b"
    groq_stt_model: str = "whisper-large-v3-turbo"
    groq_reasoning_format: str = ""
    stt_provider: str = "sarvam"
    sarvam_stt_model: str = "saaras:v3"
    sarvam_stt_mode: str = "transcribe"
    sarvam_tts_model: str = "bulbul:v3"
    sarvam_tts_speaker: str = "shubh"
    sarvam_tts_language: str = "en-IN"
    storage_backend: str = "local"
    local_user_id: str = "local-user"
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_bucket: str = "project-assets"
    frontend_url: str = "http://localhost:5173"
    enable_safety: bool = True
    enable_solve_stage: bool = True
    daily_ai_call_cap: int = 300
    safety_fail_open: bool = True
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
