from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Project(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    has_thumbnail: bool = False


class ProjectTitle(BaseModel):
    title: str = Field(min_length=1, max_length=120)

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title must not be blank")
        return value


class ProjectCreate(ProjectTitle):
    title: str = "Untitled project"


class ProjectRename(ProjectTitle):
    pass


class CanvasSave(BaseModel):
    elements: list[dict] = Field(max_length=10000)
    app_state: dict = Field(default_factory=dict)
    files: dict[str, dict] = Field(default_factory=dict, max_length=200)
    thumbnail_data_url: str | None = None
    model_config = ConfigDict(extra="ignore")


class CanvasLoad(BaseModel):
    elements: list[dict] = Field(default_factory=list)
    app_state: dict = Field(default_factory=dict)
    files: dict[str, dict] = Field(default_factory=dict)
