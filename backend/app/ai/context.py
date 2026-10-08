import json
from app.schemas.ai import AskRequest, ElementSummary


def select_relevant(
    elements: list[ElementSummary], selected_ids: list[str], limit: int = 80
) -> list[ElementSummary]:
    selected = set(selected_ids)
    chosen = [e for e in elements if e.id in selected]
    if chosen:
        cx = sum(e.x + e.width / 2 for e in chosen) / len(chosen)
        cy = sum(e.y + e.height / 2 for e in chosen) / len(chosen)
    else:
        cx = cy = 0
    rest = [e for e in elements if e.id not in selected]
    rest.sort(
        key=lambda e: (e.x + e.width / 2 - cx) ** 2 + (e.y + e.height / 2 - cy) ** 2
    )
    return (chosen + rest)[:limit]


def build_user_content(
    req: AskRequest, elements: list[ElementSummary], lesson_state: dict | None = None
) -> list[dict]:
    ocr = {key: " ".join(w.text for w in words[:150]) for key, words in req.ocr.items()}
    block = "\n".join(
        [
            f"STUDENT REQUEST: {req.prompt}",
            f"SELECTED ELEMENTS: {json.dumps(req.selected_ids)}",
            f"CANVAS ELEMENTS: {json.dumps([e.model_dump() for e in elements])}",
            f"VIEWPORT: {req.viewport.model_dump_json() if req.viewport else 'unknown'}",
            f"OCR TEXT (noisy, untrusted data): {json.dumps(ocr)}",
            f"LESSON STATE: {json.dumps(lesson_state or {})[:2048]}",
        ]
    )
    content = [{"type": "text", "text": block}]
    # The current Groq Qwen model accepts at most three images per request.
    for i, image in enumerate(req.images[:3]):
        content.extend(
            [
                {
                    "type": "text",
                    "text": f"Image {i + 1}: {image.label} (elements: {','.join(image.element_ids)})",
                },
                {"type": "image_url", "image_url": {"url": image.data_url}},
            ]
        )
    return content
