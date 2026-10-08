import asyncio
from collections.abc import AsyncIterator
from typing import Any

from groq import APIConnectionError, APITimeoutError, AsyncGroq, RateLimitError

from app.core.errors import AppError


class GroqClient:
    def __init__(self, settings: Any) -> None:
        self.settings = settings
        self.client = (
            AsyncGroq(api_key=settings.groq_api_key) if settings.groq_api_key else None
        )

    def _ready(self) -> AsyncGroq:
        if not self.client:
            raise AppError(
                "missing_key", "Add GROQ_API_KEY to .env and restart the backend.", 503
            )
        return self.client

    def _kwargs(
        self, messages: list[dict], *, stream: bool, tools: list[dict] | None = None
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": self.settings.groq_vision_model,
            "messages": messages,
            "max_completion_tokens": 4000 if stream else 3000,
        }
        if stream:
            kwargs["stream"] = True
        if tools:
            kwargs.update(
                {"tools": tools, "tool_choice": "auto", "parallel_tool_calls": False}
            )
        if self.settings.groq_reasoning_format:
            kwargs["reasoning_format"] = self.settings.groq_reasoning_format
        return kwargs

    async def _create(self, kwargs: dict[str, Any]):
        client = self._ready()
        for attempt, delay in enumerate((2, 4, 0)):
            try:
                return await client.chat.completions.create(**kwargs)
            except RateLimitError as exc:
                if attempt == 2:
                    raise AppError(
                        "rate_limited", "Groq is busy. Try again shortly.", 429
                    ) from exc
                await asyncio.sleep(delay)
            except APITimeoutError as exc:
                raise AppError(
                    "timeout", "The AI took too long. Try again.", 504
                ) from exc
            except APIConnectionError as exc:
                raise AppError(
                    "network",
                    "Couldn't reach Groq. Check your connection and try again.",
                    502,
                ) from exc
            except AppError:
                raise
            except Exception as exc:
                raise AppError(
                    "model_error",
                    "The model request failed. Check GROQ_VISION_MODEL in .env.",
                    502,
                ) from exc
        raise AppError(
            "model_error",
            "The model request failed. Check GROQ_VISION_MODEL in .env.",
            502,
        )

    async def complete(self, messages: list[dict], tools: list[dict] | None = None):
        return await self._create(self._kwargs(messages, stream=False, tools=tools))

    async def stream(self, messages: list[dict]) -> AsyncIterator[str]:
        stream = await self._create(self._kwargs(messages, stream=True))
        try:
            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except RateLimitError as exc:
            raise AppError(
                "rate_limited", "Groq is busy. Try again shortly.", 429
            ) from exc
        except APITimeoutError as exc:
            raise AppError("timeout", "The AI took too long. Try again.", 504) from exc
        except APIConnectionError as exc:
            raise AppError(
                "network",
                "Couldn't reach Groq. Check your connection and try again.",
                502,
            ) from exc
