"""Bad tool calls must come back as error text, never crash and never start anything.
Run: .venv\\Scripts\\python -m pytest"""
import pytest

import tools


@pytest.fixture(autouse=True)
def log_to_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "LOG_FILE", tmp_path / "tool_calls.log")  # keep the real log clean


def test_unknown_app():
    assert tools.run_tool("open_app", '{"name": "photoshop"}').startswith("Error: unknown app 'photoshop'")


def test_unknown_tool():
    assert tools.run_tool("delete_files", "{}").startswith("Error: unknown tool 'delete_files'")


def test_broken_json():
    assert tools.run_tool("open_app", '{"name": "notepad"').startswith("Error: bad arguments")


def test_wrong_argument_name():
    assert tools.run_tool("open_app", '{"app": "notepad"}').startswith("Error: bad arguments")


def test_arguments_not_an_object():
    assert tools.run_tool("open_app", '["notepad"]').startswith("Error: bad arguments")
