import json
from app.ai.stream_parser import JsonObjectStreamParser


def test_noisy_stream():
    parser = JsonObjectStreamParser()
    text = 'prose```json\n{"say":"brace } in text","actions":[]}\n```<think>{"hidden":1}</think>{"lesson_state":{"step":2}}'
    result = []
    for char in text:
        result.extend(parser.feed(char))
    assert result == [
        {"say": "brace } in text", "actions": []},
        {"lesson_state": {"step": 2}},
    ]


def test_split_at_every_boundary():
    value = {"say": "hello", "actions": [{"tool": "write_text", "text": "x"}]}
    raw = json.dumps(value)
    for index in range(len(raw) + 1):
        parser = JsonObjectStreamParser()
        assert parser.feed(raw[:index]) + parser.feed(raw[index:]) == [value]


def test_invalid_object_is_skipped_and_next_object_survives():
    parser = JsonObjectStreamParser()
    assert parser.feed('{"broken": nope}{"say":"safe","actions":[]}') == [
        {"say": "safe", "actions": []}
    ]
