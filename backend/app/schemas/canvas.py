from typing import Annotated, Literal, Union
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    field_validator,
    model_validator,
)


class PointTarget(BaseModel):
    x: float = Field(ge=-100000, le=100000)
    y: float = Field(ge=-100000, le=100000)
    model_config = ConfigDict(extra="ignore")


class ElementTarget(BaseModel):
    element_id: str = Field(min_length=1, max_length=80)
    region: tuple[float, float, float, float] | None = None
    text: str | None = Field(default=None, max_length=80)
    model_config = ConfigDict(extra="ignore")

    @field_validator("region")
    @classmethod
    def valid_region(cls, v):
        if v is not None and not (0 <= v[0] < v[2] <= 1 and 0 <= v[1] < v[3] <= 1):
            raise ValueError("invalid region")
        return v


Target = Union[PointTarget, ElementTarget]
Color = Literal["ink", "violet", "red", "green", "blue", "orange"]


class Action(BaseModel):
    model_config = ConfigDict(extra="ignore")


class WriteText(Action):
    tool: Literal["write_text"]
    text: str = Field(min_length=1, max_length=400)
    near: Target | None = None
    side: Literal["right", "left", "above", "below"] = "right"
    size: Literal["s", "m", "l"] = "m"
    color: Color = "ink"


class DrawArrow(Action):
    tool: Literal["draw_arrow"]
    start: Target
    end: Target
    label: str | None = Field(default=None, max_length=60)
    color: Color = "violet"


class DrawLine(Action):
    tool: Literal["draw_line"]
    start: Target
    end: Target
    color: Color = "ink"


class DrawRectangle(Action):
    tool: Literal["draw_rectangle"]
    target: Target
    padding: float = Field(default=8, ge=0, le=80)
    label: str | None = Field(default=None, max_length=60)
    color: Color = "violet"


class DrawCircle(Action):
    tool: Literal["draw_circle"]
    target: Target
    padding: float = Field(default=10, ge=0, le=80)
    color: Color = "red"


class Highlight(Action):
    tool: Literal["highlight"]
    target: Target
    color: Color = "orange"


class PointTo(Action):
    tool: Literal["point_to"]
    target: Target
    label: str | None = Field(default=None, max_length=60)


class ZoomTo(Action):
    tool: Literal["zoom_to"]
    target: Target


class DeleteAIElement(Action):
    tool: Literal["delete_ai_element"]
    element_id: str = Field(min_length=1, max_length=80)


CanvasAction = Annotated[
    Union[
        WriteText,
        DrawArrow,
        DrawLine,
        DrawRectangle,
        DrawCircle,
        Highlight,
        PointTo,
        ZoomTo,
        DeleteAIElement,
    ],
    Field(discriminator="tool"),
]
ACTION_ADAPTER = TypeAdapter(CanvasAction)


class Step(BaseModel):
    say: str | None = Field(default=None, max_length=400)
    actions: list[CanvasAction] = Field(default_factory=list, max_length=12)
    wait_for_student: bool = False
    question: str | None = Field(default=None, max_length=300)
    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="after")
    def useful(self):
        if not self.say and not self.actions and not self.wait_for_student:
            raise ValueError("empty step")
        return self
