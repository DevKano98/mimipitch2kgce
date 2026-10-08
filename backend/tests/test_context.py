from app.ai.context import build_user_content, select_relevant
from app.schemas.ai import AskRequest, ElementSummary


def test_relevant_keeps_selected_and_caps():
    items = [
        ElementSummary(id=str(i), type="text", x=i, y=0, width=1, height=1)
        for i in range(100)
    ]
    result = select_relevant(items, ["99"])
    assert result[0].id == "99" and len(result) == 80


def test_context_labels_untrusted_ocr():
    req = AskRequest(
        project_id="p",
        prompt="help",
        ocr={"img": [{"text": "word", "box": [0, 0, 1, 1]}]},
    )
    content = build_user_content(req, [])
    assert "untrusted" in content[0]["text"] and "word" in content[0]["text"]
