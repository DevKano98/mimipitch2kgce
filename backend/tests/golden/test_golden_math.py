import json
from pathlib import Path

import pytest

from app.tools.math import run_math_tool_sync


CASES = json.loads((Path(__file__).with_name("cases.json")).read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_verified_math_golden_set(case):
    actual = run_math_tool_sync(case["tool"], case["args"])
    assert "error" not in actual
    for key, expected in case["expected"].items():
        if key == "solutions":
            assert set(actual[key]) == set(expected)
        else:
            assert actual[key] == expected
