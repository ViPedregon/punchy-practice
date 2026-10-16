import pytest

from punchy import tools
from punchy.tools import run_tool


@pytest.fixture(autouse=True)
def workspace(tmp_path, monkeypatch):
    (tmp_path / "notes.txt").write_text("hello")
    (tmp_path / "sub").mkdir()
    monkeypatch.setattr(tools, "WORKSPACE", tmp_path.resolve())
    return tmp_path


def test_calculator():
    assert run_tool("calculator", {"expression": "(3 + 4) * 2"}) == ("14", False)
    assert run_tool("calculator", {"expression": "-2 ** 2"}) == ("-4", False)


@pytest.mark.parametrize("expr", ["1/0", "__import__('os')", "2 ** 99999", "1 +"])
def test_calculator_rejects_bad_input(expr):
    _, is_error = run_tool("calculator", {"expression": expr})
    assert is_error


def test_list_and_read():
    assert run_tool("list_files", {"path": "."}) == ("notes.txt\nsub/", False)
    assert run_tool("read_file", {"path": "notes.txt"}) == ("hello", False)


@pytest.mark.parametrize("path", ["../outside.txt", "/etc/passwd"])
def test_paths_cannot_escape_workspace(path):
    output, is_error = run_tool("read_file", {"path": path})
    assert is_error and "outside the workspace" in output


def test_unknown_tool():
    assert run_tool("nope", {}) == ("Unknown tool: nope", True)
