import ast
import re
from concurrent.futures import ProcessPoolExecutor, TimeoutError
from typing import Any

import sympy as sp

ALLOWED_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Constant,
    ast.Name,
    ast.Call,
    ast.Load,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Pow,
    ast.Mod,
    ast.USub,
    ast.UAdd,
)
FUNCS = {
    "sin": sp.sin,
    "cos": sp.cos,
    "tan": sp.tan,
    "asin": sp.asin,
    "acos": sp.acos,
    "atan": sp.atan,
    "sinh": sp.sinh,
    "cosh": sp.cosh,
    "tanh": sp.tanh,
    "sqrt": sp.sqrt,
    "exp": sp.exp,
    "log": sp.log,
    "ln": sp.log,
    "Abs": sp.Abs,
    "floor": sp.floor,
    "ceiling": sp.ceiling,
    "radians": lambda x: x * sp.pi / 180,
    "degrees": lambda x: x * 180 / sp.pi,
}
CONSTANTS = {"pi": sp.pi, "E": sp.E}
NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,15}$")
MATH_TOOL_NAMES = (
    "calculate",
    "solve_equation",
    "simplify",
    "expand",
    "factor",
    "differentiate",
    "integrate",
)


def _clean(value: str) -> str:
    return (
        value.replace("^", "**")
        .replace("×", "*")
        .replace("÷", "/")
        .replace("−", "-")
        .replace("θ", "theta")
        .replace("π", "pi")
        .replace("°", "*pi/180")
    )


def safe_expression(value: str):
    value = _clean(value.strip())
    if not value or len(value) > 300 or "__" in value:
        raise ValueError("invalid expression")
    tree = ast.parse(value, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_NODES):
            raise ValueError(f"unsupported syntax: {type(node).__name__}")
        if isinstance(node, ast.Constant) and (
            isinstance(node.value, bool) or not isinstance(node.value, (int, float))
        ):
            raise ValueError("only numeric constants are allowed")
        if isinstance(node, ast.Name) and not NAME_RE.fullmatch(node.id):
            raise ValueError("invalid name")
        if isinstance(node, ast.Call) and (
            not isinstance(node.func, ast.Name)
            or node.func.id not in FUNCS
            or node.keywords
        ):
            raise ValueError("function not allowed")
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    local = (
        dict(FUNCS)
        | dict(CONSTANTS)
        | {
            name: sp.Symbol(name)
            for name in names
            if name not in FUNCS and name not in CONSTANTS
        }
    )
    return sp.sympify(value, locals=local, evaluate=True)


def _numeric(value: Any):
    try:
        result = float(sp.N(value))
        return result if abs(result) < 1e100 else None
    except (TypeError, ValueError, OverflowError):
        return None


def run_math_tool_sync(name: str, args: dict[str, Any]) -> dict[str, Any]:
    try:
        source = str(args.get("expression", args.get("equation", "")))
        if name == "solve_equation" and "=" in source:
            left, right = source.split("=", 1)
            expression = safe_expression(left) - safe_expression(right)
        else:
            expression = safe_expression(source)
        variable = str(args.get("variable", "x"))
        if not NAME_RE.fullmatch(variable):
            raise ValueError("invalid variable")
        symbol = sp.Symbol(variable)
        if name == "calculate":
            result = expression
        elif name == "simplify":
            result = sp.simplify(expression)
        elif name == "expand":
            result = sp.expand(expression)
        elif name == "factor":
            result = sp.factor(expression)
        elif name == "differentiate":
            result = sp.diff(expression, symbol)
        elif name == "integrate":
            result = (
                sp.integrate(
                    expression,
                    (
                        symbol,
                        safe_expression(str(args["lower"])),
                        safe_expression(str(args["upper"])),
                    ),
                )
                if args.get("lower") is not None and args.get("upper") is not None
                else sp.integrate(expression, symbol)
            )
        elif name == "solve_equation":
            solutions = sp.solve(expression, symbol)
            return {
                "solutions": [str(v) for v in solutions],
                "numeric": [_numeric(v) for v in solutions],
            }
        else:
            return {"error": "unknown math tool"}
        return {"result": str(result), "numeric": _numeric(result)}
    except Exception as exc:
        return {"error": str(exc)[:200]}


_POOL: ProcessPoolExecutor | None = None


def run_math_tool(
    name: str, args: dict[str, Any], timeout: float = 8
) -> dict[str, Any]:
    global _POOL
    if _POOL is None:
        _POOL = ProcessPoolExecutor(max_workers=1)
    try:
        return _POOL.submit(run_math_tool_sync, name, args).result(timeout=timeout)
    except TimeoutError:
        _POOL.shutdown(wait=False, cancel_futures=True)
        _POOL = None
        return {"error": "calculation timed out"}
    except Exception:
        _POOL = None
        return {"error": "calculation failed"}
