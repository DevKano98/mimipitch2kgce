from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel, Field
from app.dependencies import get_speech

router = APIRouter()


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2500)
    language_code: str | None = None


@router.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    language: str | None = Form(None),
    speech=Depends(get_speech),
):
    data = await file.read()
    if len(data) > 15_000_000:
        from app.core.errors import AppError

        raise AppError(
            "invalid", "Audio is too large. Keep recordings below 30 seconds.", 413
        )
    return await speech.transcribe(
        data,
        file.filename or "recording.wav",
        file.content_type or "audio/wav",
        language,
    )


@router.post("/speak")
async def speak(body: SpeakRequest, speech=Depends(get_speech)):
    return await speech.speak(body.text, body.language_code)
