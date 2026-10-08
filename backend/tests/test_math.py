import pytest
from app.tools.math import run_math_tool_sync, safe_expression


@pytest.mark.parametrize(
    "bad",
    [
        "__import__('os')",
        "os.system('x')",
        "lambda: 1",
        "[1,2]",
        "x.real",
        "'text'",
        "x" * 301,
    ],
)
def test_rejects_unsafe_math(bad):
    with pytest.raises((ValueError, SyntaxError)):
        safe_expression(bad)


def test_math_tools():
    assert str(safe_expression("2*x+1")) == "2*x + 1"
    assert (
        run_math_tool_sync("calculate", {"expression": "sqrt(2)*10"})["result"]
        == "10*sqrt(2)"
    )
    assert set(
        run_math_tool_sync("solve_equation", {"equation": "x**2-4=0", "variable": "x"})[
            "solutions"
        ]
    ) == {"-2", "2"}
    assert (
        run_math_tool_sync("differentiate", {"expression": "x**3", "variable": "x"})[
            "result"
        ]
        == "3*x**2"
    )
    assert (
        run_math_tool_sync(
            "integrate", {"expression": "x", "variable": "x", "lower": 0, "upper": 1}
        )["result"]
        == "1/2"
    )


def test_unicode_math_input_is_normalized():
    assert (
        run_math_tool_sync("calculate", {"expression": "sin(30°)"})["result"] == "1/2"
    )
    assert run_math_tool_sync("calculate", {"expression": "6×7"})["numeric"] == 42
    assert run_math_tool_sync("calculate", {"expression": "8÷4"})["numeric"] == 2
    assert run_math_tool_sync("simplify", {"expression": "θ−θ"})["numeric"] == 0
