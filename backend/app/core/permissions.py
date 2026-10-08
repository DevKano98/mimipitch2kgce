from app.schemas.ai import ElementSummary
from app.schemas.canvas import CanvasAction, DeleteAIElement, ElementTarget


def referenced_ids(action: CanvasAction) -> set[str]:
    ids: set[str] = set()
    for name in ("near", "start", "end", "target"):
        value = getattr(action, name, None)
        if isinstance(value, ElementTarget):
            ids.add(value.element_id)
    if isinstance(action, DeleteAIElement):
        ids.add(action.element_id)
    return ids


def allowed(
    action: CanvasAction, elements: list[ElementSummary]
) -> tuple[bool, str | None]:
    known = {e.id: e for e in elements}
    missing = referenced_ids(action) - known.keys()
    if missing:
        return False, f"unknown element '{next(iter(missing))}'"
    if (
        isinstance(action, DeleteAIElement)
        and known[action.element_id].created_by != "ai"
    ):
        return False, "cannot delete student work"
    return True, None
