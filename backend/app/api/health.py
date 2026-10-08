from fastapi import APIRouter, Depends
from app.core.config import Settings, get_settings

router = APIRouter()


@router.get("/health")
def health(s: Settings = Depends(get_settings)):
    return {
        "ok": True,
        "groq_configured": bool(s.groq_api_key),
        "sarvam_configured": bool(s.sarvam_api_key),
        "storage": s.storage_backend,
        "models": {
            "vision": s.groq_vision_model,
            "safety": s.groq_safety_model,
            "stt": s.groq_stt_model,
        },
    }
