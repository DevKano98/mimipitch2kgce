import asyncio, json, uuid
from collections.abc import Awaitable, Callable
from app.ai.context import build_user_content, select_relevant
from app.ai.prompts import SOLVER, system_prompt
from app.ai.stream_parser import JsonObjectStreamParser
from app.schemas.ai import AskRequest
from app.tools.canvas import validate_step
from app.tools.math import MATH_TOOL_NAMES, run_math_tool

MATH_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": name,
            "description": f"Safely {name.replace('_', ' ')} with SymPy. Use explicit * and **; trigonometry uses radians.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string"},
                    "equation": {"type": "string"},
                    "variable": {"type": "string"},
                    "lower": {"type": ["string", "number"]},
                    "upper": {"type": ["string", "number"]},
                },
                "additionalProperties": False,
            },
        },
    }
    for name in MATH_TOOL_NAMES
]

Emit = Callable[[dict], Awaitable[None]]


class Orchestrator:
    def __init__(self, llm, safety, settings, usage):
        self.llm, self.safety, self.s, self.usage = llm, safety, settings, usage

    async def _solve(self, content):
        if not self.s.enable_solve_stage:
            return "", False
        try:
            messages = [
                {"role": "system", "content": SOLVER},
                {"role": "user", "content": content},
            ]
            verified = []
            for _ in range(4):
                response = await self.llm.complete(messages, tools=MATH_TOOLS)
                message = response.choices[0].message
                calls = getattr(message, "tool_calls", None) or []
                messages.append(
                    {
                        "role": "assistant",
                        "content": message.content or "",
                        "tool_calls": [
                            {
                                "id": call.id,
                                "type": "function",
                                "function": {
                                    "name": call.function.name,
                                    "arguments": call.function.arguments,
                                },
                            }
                            for call in calls
                        ],
                    }
                )
                if not calls:
                    return "\n".join(verified + [message.content or ""]), False
                for call in calls:
                    try:
                        args = json.loads(call.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    result = await asyncio.to_thread(
                        run_math_tool, call.function.name, args
                    )
                    verified.append(f"{call.function.name}({args}) = {result}")
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "content": json.dumps(result),
                        }
                    )
            return "\n".join(verified), False
        except Exception:
            return "", True

    async def run(self, req: AskRequest, emit: Emit, history=None, lesson_state=None):
        self.usage.hit()
        await emit({"type": "status", "message": "Checking request…"})
        safety_task = asyncio.create_task(self.safety.check(req.prompt))
        relevant = select_relevant(req.elements, req.selected_ids)
        content = build_user_content(req, relevant, lesson_state)
        if safety_task.done() and not safety_task.result():
            await emit(
                {
                    "type": "error",
                    "code": "safety",
                    "message": "That request can't be carried out safely. Rephrase it as a learning or drawing request.",
                }
            )
            return
        notes, solve_failed = await self._solve(content)
        if not await safety_task:
            await emit(
                {
                    "type": "error",
                    "code": "safety",
                    "message": "That request can't be carried out safely. Rephrase it as a learning or drawing request.",
                }
            )
            return
        if solve_failed:
            await emit(
                {
                    "type": "warning",
                    "message": "The verification step was unavailable, so the explanation will avoid relying on unverified calculations.",
                }
            )
        await emit({"type": "status", "message": "Planning the explanation…"})
        messages = (
            [{"role": "system", "content": system_prompt(req.mode, notes)}]
            + (history or [])[-6:]
            + [{"role": "user", "content": content}]
        )
        parser = JsonObjectStreamParser()
        steps = []
        state = None
        try:
            async for chunk in self.llm.stream(messages):
                for raw in parser.feed(chunk):
                    if "lesson_state" in raw:
                        state = raw["lesson_state"]
                        continue
                    if len(steps) >= 12:
                        continue
                    step, warnings = validate_step(raw, relevant)
                    for warning in warnings:
                        await emit({"type": "warning", "message": warning})
                    if step:
                        steps.append(step)
                        await emit(
                            {
                                "type": "step",
                                "index": len(steps) - 1,
                                "step": step.model_dump(mode="json"),
                            }
                        )
        except asyncio.CancelledError:
            raise
        if not steps:
            await emit(
                {
                    "type": "error",
                    "code": "invalid",
                    "message": "The AI response couldn't be used. No changes were made. Try again.",
                }
            )
            return
        await emit(
            {
                "type": "done",
                "action_id": str(uuid.uuid4()),
                "steps": len(steps),
                "text": " ".join(s.say or "" for s in steps),
                "lesson_state": state,
            }
        )
