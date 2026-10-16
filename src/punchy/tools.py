"""Tools the agent can call.

A tool has two halves:
  1. A schema (TOOLS) that tells Claude the tool exists and what arguments it takes.
  2. A Python function that actually runs when Claude asks for it.

Claude never runs code itself. It replies with a `tool_use` block, our loop runs
the matching function, and we send the output back as a `tool_result`.
"""

import ast
import operator
from pathlib import Path

# The agent can only read files under this directory.
WORKSPACE = Path.cwd().resolve()

TOOLS = [
    {
        "name": "calculator",
        "description": "Evaluate an arithmetic expression. Supports + - * / // % ** and parentheses.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "For example, '(3 + 4) * 2'"},
            },
            "required": ["expression"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "name": "list_files",
        "description": "List files and directories at a path inside the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path relative to the workspace root. Use '.' for the root."},
            },
            "required": ["path"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "name": "read_file",
        "description": "Read a UTF-8 text file inside the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path relative to the workspace root."},
            },
            "required": ["path"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


class ToolError(Exception):
    """A failure to report back to Claude (as is_error) rather than crash on."""


_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval(node: ast.AST) -> float:
    # Walk the parsed expression ourselves instead of calling eval(), which
    # would let the model run arbitrary Python.
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        if isinstance(node.op, ast.Pow) and abs(_eval(node.right)) > 1000:
            raise ToolError("Exponent too large")
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    raise ToolError(f"Unsupported expression element: {ast.dump(node)}")


def calculator(expression: str) -> str:
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as e:
        raise ToolError(f"Invalid expression: {e.msg}")
    try:
        return str(_eval(tree.body))
    except ZeroDivisionError:
        raise ToolError("Division by zero")


def _resolve(path: str) -> Path:
    target = (WORKSPACE / path).resolve()
    if not target.is_relative_to(WORKSPACE):
        raise ToolError(f"Path is outside the workspace: {path}")
    return target


def list_files(path: str) -> str:
    target = _resolve(path)
    if not target.is_dir():
        raise ToolError(f"Not a directory: {path}")
    entries = sorted(
        p.name + ("/" if p.is_dir() else "")
        for p in target.iterdir()
        if not p.name.startswith(".")
    )
    return "\n".join(entries) or "(empty)"


def read_file(path: str) -> str:
    target = _resolve(path)
    if not target.is_file():
        raise ToolError(f"Not a file: {path}")
    try:
        return target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise ToolError(f"Not a UTF-8 text file: {path}")


HANDLERS = {
    "calculator": calculator,
    "list_files": list_files,
    "read_file": read_file,
}


def run_tool(name: str, args: dict) -> tuple[str, bool]:
    """Run a tool by name. Returns (output, is_error)."""
    handler = HANDLERS.get(name)
    if handler is None:
        return f"Unknown tool: {name}", True
    try:
        return handler(**args), False
    except ToolError as e:
        return str(e), True
