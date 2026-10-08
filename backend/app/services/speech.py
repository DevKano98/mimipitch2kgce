import httpx
from app.core.errors import AppError


class SpeechService:
    def __init__(self, settings, client=None):
        self.s = settings
        self.client = client or httpx.AsyncClient(timeout=35)

    async def transcribe(self, data, filename, mime, language):
        if self.s.stt_provider == "groq":
            if not self.s.groq_api_key:
                raise AppError(
                    "missing_key",
                    "Add GROQ_API_KEY to .env and restart the backend.",
                    503,
                )
            headers = {"Authorization": f"Bearer {self.s.groq_api_key}"}
            files = {"file": (filename, data, mime)}
            form = {"model": self.s.groq_stt_model}
            url = "https://api.groq.com/openai/v1/audio/transcriptions"
            if language and language != "unknown":
                form["language"] = "hi" if language.startswith("hi") else "en"
        else:
            if not self.s.sarvam_api_key:
                raise AppError(
                    "missing_key",
                    "Add SARVAM_API_KEY to .env and restart the backend.",
                    503,
                )
            headers = {"api-subscription-key": self.s.sarvam_api_key}
            files = {"file": (filename, data, mime)}
            form = {
                "model": self.s.sarvam_stt_model,
                "mode": self.s.sarvam_stt_mode,
                "language_code": language or "unknown",
            }
            url = "https://api.sarvam.ai/speech-to-text"
        try:
            r = await self.client.post(url, headers=headers, files=files, data=form)
            r.raise_for_status()
            body = r.json()
            return {
                "transcript": body.get("transcript") or body.get("text", "").strip(),
                "language_code": body.get("language_code", language or "unknown"),
                "provider": self.s.stt_provider,
            }
        except httpx.HTTPError as exc:
            raise AppError(
                "network",
                "Speech recognition failed. Try again or type the request.",
                502,
            ) from exc

    async def speak(self, text, language=None):
        if not self.s.sarvam_api_key:
            raise AppError(
                "missing_key",
                "Add SARVAM_API_KEY to .env and restart the backend.",
                503,
            )
        try:
            r = await self.client.post(
                "https://api.sarvam.ai/text-to-speech",
                headers={"api-subscription-key": self.s.sarvam_api_key},
                json={
                    "text": text,
                    "language_code": language or self.s.sarvam_tts_language,
                    "speaker": self.s.sarvam_tts_speaker,
                    "model": self.s.sarvam_tts_model,
                    "output_audio_codec": "wav",
                },
            )
            r.raise_for_status()
            body = r.json()
            return {"audio_base64": body["audios"][0], "mime": "audio/wav"}
        except (httpx.HTTPError, KeyError, IndexError) as exc:
            raise AppError(
                "network",
                "Voice playback failed. The written caption is still available.",
                502,
            ) from exc
