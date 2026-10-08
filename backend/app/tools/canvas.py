from pydantic import ValidationError
from app.core.permissions import allowed
from app.schemas.ai import ElementSummary
from app.schemas.canvas import ACTION_ADAPTER, Step


def normalize_action(item: dict) -> dict:
    if not isinstance(item, dict):
        return item
    raw = dict(item)
    if "args" in raw and isinstance(raw["args"], dict):
        args = dict(raw.pop("args"))
        raw = {**args, **raw}
    tool = raw.get("tool")
    if tool == "write_text" and "text" not in raw:
        for alt in ("content", "label", "value"):
            if alt in raw:
                raw["text"] = str(raw.pop(alt))
                break
    if tool in ("draw_arrow", "draw_line"):
        if "start" not in raw and "from" in raw:
            raw["start"] = raw.pop("from")
        if "end" not in raw and "to" in raw:
            raw["end"] = raw.pop("to")
    if (
        tool in ("draw_rectangle", "draw_circle", "highlight", "point_to", "zoom_to")
        and "target" not in raw
    ):
        for alt in ("near", "element", "element_id"):
            if alt in raw:
                raw["target"] = raw.pop(alt)
                break
    for field in ("near", "target", "start", "end"):
        val = raw.get(field)
        if isinstance(val, str) and val.strip():
            raw[field] = {"element_id": val.strip()}
    if "side" in raw:
        side = str(raw["side"]).lower()
        side_map = {
            "bottom": "below",
            "top": "above",
            "under": "below",
            "over": "above",
        }
        raw["side"] = side_map.get(
            side, side if side in ("right", "left", "above", "below") else "right"
        )
    if "size" in raw:
        s = raw["size"]
        if isinstance(s, (int, float)):
            raw["size"] = "s" if s <= 16 else ("m" if s <= 22 else "l")
        elif isinstance(s, str) and s.lower() not in ("s", "m", "l"):
            raw["size"] = "m"
    if "color" in raw and isinstance(raw["color"], str):
        c = raw["color"].lower()
        color_map = {
            "black": "ink",
            "dark": "ink",
            "purple": "violet",
            "navy": "blue",
            "cyan": "blue",
            "yellow": "orange",
        }
        raw["color"] = color_map.get(
            c, c if c in ("ink", "violet", "red", "green", "blue", "orange") else "ink"
        )
    return raw


def validate_step(
    raw: dict, elements: list[ElementSummary]
) -> tuple[Step | None, list[str]]:
    warnings = []
    actions = []
    for item in list(raw.get("actions") or [])[:12]:
        try:
            norm = normalize_action(item) if isinstance(item, dict) else item
            action = ACTION_ADAPTER.validate_python(norm)
            ok, reason = allowed(action, elements)
            if ok:
                actions.append(action)
            else:
                warnings.append(
                    f"blocked {getattr(action, 'tool', 'action')}: {reason}"
                )
        except ValidationError as exc:
            warnings.append(f"invalid action: {exc.errors()[0]['msg']}")
    candidate = {**raw, "actions": actions}
    try:
        return Step.model_validate(candidate), warnings
    except ValidationError:
        return None, warnings
