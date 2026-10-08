import json
import httpx
import pytest
from app.core.errors import AppError
from app.services.speech import SpeechService


class Settings:
    stt_provider = "sarvam"
    sarvam_api_key = "secret"
    groq_api_key = "secret"
    sarvam_stt_model = "saaras:v3"
    sarvam_stt_mode = "transcribe"
    groq_stt_model = "whisper-large-v3-turbo"
    sarvam_tts_language = "en-IN"
    sarvam_tts_speaker = "shubh"
    sarvam_tts_model = "bulbul:v3"


@pytest.mark.asyncio
async def test_sarvam_tts_shape():
    async def handler(request: httpx.Request):
        body = json.loads(request.content)
        assert request.headers["api-subscription-key"] == "secret"
        assert (
            body["language_code"] == "hi-IN"
            and body["model"] == "bulbul:v3"
            and body["output_audio_codec"] == "wav"
        )
        return httpx.Response(200, json={"audios": ["audio"]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        assert (await SpeechService(Settings(), client).speak("नमस्ते", "hi-IN"))[
            "audio_base64"
        ] == "audio"


@pytest.mark.asyncio
async def test_sarvam_stt_shape():
    async def handler(request: httpx.Request):
        content = request.content.decode("utf-8", errors="ignore")
        assert str(request.url) == "https://api.sarvam.ai/speech-to-text"
        assert request.headers["api-subscription-key"] == "secret"
        assert 'name="model"' in content and "saaras:v3" in content
        assert 'name="mode"' in content and "transcribe" in content
        assert 'name="language_code"' in content and "hi-IN" in content
        assert 'filename="clip.wav"' in content
        return httpx.Response(
            200, json={"transcript": "नमस्ते", "language_code": "hi-IN"}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await SpeechService(Settings(), client).transcribe(
            b"wave", "clip.wav", "audio/wav", "hi-IN"
        )
        assert result == {
            "transcript": "नमस्ते",
            "language_code": "hi-IN",
            "provider": "sarvam",
        }


@pytest.mark.asyncio
async def test_groq_stt_shape_and_language_mapping():
    class GroqSettings(Settings):
        stt_provider = "groq"

    async def handler(request: httpx.Request):
        content = request.content.decode("utf-8", errors="ignore")
        assert str(request.url) == "https://api.groq.com/openai/v1/audio/transcriptions"
        assert request.headers["authorization"] == "Bearer secret"
        assert (
            "whisper-large-v3-turbo" in content
            and 'name="language"' in content
            and "hi" in content
        )
        return httpx.Response(200, json={"text": "hello"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await SpeechService(GroqSettings(), client).transcribe(
            b"wave", "clip.wav", "audio/wav", "hi-IN"
        )
        assert result["transcript"] == "hello" and result["provider"] == "groq"


@pytest.mark.asyncio
async def test_missing_speech_keys_are_friendly():
    class Missing(Settings):
        sarvam_api_key = ""
        groq_api_key = ""

    with pytest.raises(AppError) as error:
        await SpeechService(Missing()).speak("hello")
    assert error.value.code == "missing_key" and error.value.status == 503
