from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ElementSummary(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    type: str = Field(max_length=40)
    x: float
    y: float
    width: float = Field(ge=0)
    height: float = Field(ge=0)
    text: str | None = Field(default=None, max_length=120)
    created_by: Literal["user", "ai"] = "user"
    model_config = ConfigDict(extra="ignore")


class Viewport(BaseModel):
    x: float
    y: float
    width: float
    height: float
    zoom: float


class ContextImage(BaseModel):
    label: str = Field(max_length=120)
    data_url: str
    element_ids: list[str] = Field(default_factory=list)

    @field_validator("data_url")
    @classmethod
    def image_data(cls, v):
        if not v.startswith("data:image/") or len(v) > 7_000_000:
            raise ValueError("invalid image data URL")
        return v


class OcrWord(BaseModel):
    text: str
    box: tuple[float, float, float, float]


class AskRequest(BaseModel):
    project_id: str
    prompt: str = Field(min_length=1, max_length=4000)
    mode: Literal["auto", "answer", "explain", "show_me", "solve_with_me"] = "auto"
    language: str | None = None
    selected_ids: list[str] = Field(default_factory=list)
    elements: list[ElementSummary] = Field(default_factory=list, max_length=400)
    viewport: Viewport | None = None
    images: list[ContextImage] = Field(default_factory=list, max_length=4)
    ocr: dict[str, list[OcrWord]] = Field(default_factory=dict)
    model_config = ConfigDict(extra="ignore")
