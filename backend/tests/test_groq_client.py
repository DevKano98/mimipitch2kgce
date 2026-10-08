from types import SimpleNamespace

import httpx
import pytest
from groq import RateLimitError

from app.ai.groq_client import GroqClient
from app.core.errors import AppError


class Settings:
    groq_api_key = "secret"
    groq_vision_model = "model-from-env"
    groq_reasoning_format = ""


class Completions:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def rate_limit():
    request = httpx.Request("POST", "https://api.groq.test")
    return RateLimitError(
        "busy", response=httpx.Response(429, request=request), body=None
    )


@pytest.mark.asyncio
async def test_uses_env_model_and_retries_rate_limit(monkeypatch):
    response = SimpleNamespace(choices=[])
    completions = Completions([rate_limit(), response])
    client = GroqClient(Settings())
    client.client = SimpleNamespace(chat=SimpleNamespace(completions=completions))

    async def no_sleep(_):
        return None

    monkeypatch.setattr("app.ai.groq_client.asyncio.sleep", no_sleep)
    assert await client.complete([{"role": "user", "content": "hello"}]) is response
    assert (
        len(completions.calls) == 2
        and completions.calls[0]["model"] == "model-from-env"
    )


@pytest.mark.asyncio
async def test_rate_limit_exhaustion_has_stable_error(monkeypatch):
    client = GroqClient(Settings())
    client.client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=Completions([rate_limit(), rate_limit(), rate_limit()])
        )
    )

    async def no_sleep(_):
        return None

    monkeypatch.setattr("app.ai.groq_client.asyncio.sleep", no_sleep)
    with pytest.raises(AppError) as error:
        await client.complete([])
    assert error.value.code == "rate_limited" and error.value.status == 429


@pytest.mark.asyncio
async def test_missing_key_fails_before_network():
    missing = SimpleNamespace(
        groq_api_key="", groq_vision_model="model", groq_reasoning_format=""
    )
    with pytest.raises(AppError) as error:
        await GroqClient(missing).complete([])
    assert error.value.code == "missing_key" and error.value.status == 503
