import pytest
from pydantic import ValidationError
from app.core.permissions import allowed
from app.schemas.ai import ElementSummary
from app.schemas.canvas import ACTION_ADAPTER, Step
from app.tools.canvas import validate_step
from app.ai.prompts import TOOL_DOC


def elements():
    return [
        ElementSummary(id="student", type="text", x=0, y=0, width=10, height=10),
        ElementSummary(
            id="ai", type="text", x=20, y=0, width=10, height=10, created_by="ai"
        ),
    ]


def test_action_validation_and_permissions():
    action = ACTION_ADAPTER.validate_python(
        {
            "tool": "draw_circle",
            "target": {"element_id": "student", "region": [0, 0.1, 1, 0.9]},
        }
    )
    assert allowed(action, elements())[0]
    with pytest.raises(ValidationError):
        ACTION_ADAPTER.validate_python(
            {
                "tool": "draw_circle",
                "target": {"element_id": "student", "region": [0.8, 0, 0.2, 1]},
            }
        )
    with pytest.raises(ValidationError):
        ACTION_ADAPTER.validate_python({"tool": "unknown"})
    assert not allowed(
        ACTION_ADAPTER.validate_python(
            {"tool": "delete_ai_element", "element_id": "student"}
        ),
        elements(),
    )[0]
    assert allowed(
        ACTION_ADAPTER.validate_python(
            {"tool": "delete_ai_element", "element_id": "ai"}
        ),
        elements(),
    )[0]


def test_validate_step_drops_invalid_actions():
    step, warnings = validate_step(
        {
            "say": "Look here",
            "actions": [
                {"tool": "point_to", "target": {"element_id": "missing"}},
                {"tool": "highlight", "target": {"element_id": "student"}},
            ],
        },
        elements(),
    )
    assert isinstance(step, Step) and len(step.actions) == 1 and warnings


def test_prompt_documents_every_canvas_tool():
    names = set(ACTION_ADAPTER.json_schema()["discriminator"]["mapping"])
    assert names == {
        "write_text",
        "draw_arrow",
        "draw_line",
        "draw_rectangle",
        "draw_circle",
        "highlight",
        "point_to",
        "zoom_to",
        "delete_ai_element",
    }
    assert all(name in TOOL_DOC for name in names)
