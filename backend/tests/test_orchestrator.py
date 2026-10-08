import asyncio
import json
from types import SimpleNamespace
import pytest
from app.ai.orchestrator import Orchestrator
from app.schemas.ai import AskRequest, ElementSummary


class Usage:
    def hit(self):
        pass


class Safety:
    def __init__(self, allowed=True):
        self.allowed = allowed

    async def check(self, _):
        return self.allowed


class LLM:
    async def complete(self, *_, **__):
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="No calculation needed", tool_calls=[]
                    )
                )
            ]
        )

    async def stream(self, _):
        for chunk in [
            '{"say":"Look',
            ' here","actions":[{"tool":"highlight","target":{"element_id":"x"}}]}',
        ]:
            yield chunk


class Settings:
    enable_solve_stage = True


class FailingSolveLLM(LLM):
    async def complete(self, *_, **__):
        raise RuntimeError("provider failed")


class MathLLM(LLM):
    def __init__(self):
        self.calls = 0
        self.stream_messages = []

    async def complete(self, *_, **__):
        self.calls += 1
        if self.calls == 1:
            function = SimpleNamespace(
                name="calculate", arguments=json.dumps({"expression": "2+2"})
            )
            tool_call = SimpleNamespace(id="math-1", function=function)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content="", tool_calls=[tool_call])
                    )
                ]
            )
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="Verified.", tool_calls=[])
                )
            ]
        )

    async def stream(self, messages):
        self.stream_messages = messages
        yield '{"say":"Four","actions":[{"tool":"write_text","text":"4"}]}'


class InvalidLLM(LLM):
    async def stream(self, _):
        yield '{"actions":[{"tool":"delete_ai_element","element_id":"student"}]}'


class SlowLLM(LLM):
    async def stream(self, _):
        await asyncio.sleep(30)
        yield "{}"


@pytest.mark.asyncio
async def test_orchestrator_emits_steps_and_done():
    events = []
    req = AskRequest(
        project_id="p",
        prompt="help",
        elements=[ElementSummary(id="x", type="text", x=0, y=0, width=10, height=10)],
    )

    async def emit(event):
        events.append(event)

    await Orchestrator(LLM(), Safety(), Settings(), Usage()).run(req, emit)
    assert [e["type"] for e in events] == ["status", "status", "step", "done"]


@pytest.mark.asyncio
async def test_safety_block_emits_no_steps():
    events = []
    req = AskRequest(project_id="p", prompt="bad")

    async def emit(event):
        events.append(event)

    await Orchestrator(LLM(), Safety(False), Settings(), Usage()).run(req, emit)
    assert (
        not any(e["type"] == "step" for e in events) and events[-1]["code"] == "safety"
    )


@pytest.mark.asyncio
async def test_solve_failure_degrades_with_warning():
    events = []
    req = AskRequest(
        project_id="p",
        prompt="help",
        elements=[ElementSummary(id="x", type="text", x=0, y=0, width=10, height=10)],
    )

    async def emit(event):
        events.append(event)

    await Orchestrator(FailingSolveLLM(), Safety(), Settings(), Usage()).run(req, emit)
    assert any(e["type"] == "warning" for e in events) and events[-1]["type"] == "done"


@pytest.mark.asyncio
async def test_stage_a_verified_result_reaches_teaching_prompt():
    events = []
    llm = MathLLM()
    req = AskRequest(project_id="p", prompt="what is two plus two")

    async def emit(event):
        events.append(event)

    await Orchestrator(llm, Safety(), Settings(), Usage()).run(req, emit)
    system = next(
        message["content"]
        for message in llm.stream_messages
        if message["role"] == "system"
    )
    assert "calculate({'expression': '2+2'})" in system and "'result': '4'" in system
    assert events[-1]["type"] == "done"


@pytest.mark.asyncio
async def test_zero_usable_steps_changes_nothing():
    events = []
    req = AskRequest(
        project_id="p",
        prompt="delete",
        elements=[
            ElementSummary(id="student", type="text", x=0, y=0, width=10, height=10)
        ],
    )

    async def emit(event):
        events.append(event)

    await Orchestrator(InvalidLLM(), Safety(), Settings(), Usage()).run(req, emit)
    assert not any(event["type"] == "step" for event in events)
    assert events[-1]["type"] == "error" and events[-1]["code"] == "invalid"


@pytest.mark.asyncio
async def test_cancellation_stops_before_any_canvas_step():
    events = []
    req = AskRequest(project_id="p", prompt="help")

    async def emit(event):
        events.append(event)

    task = asyncio.create_task(
        Orchestrator(SlowLLM(), Safety(), Settings(), Usage()).run(req, emit)
    )
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not any(event["type"] == "step" for event in events)
