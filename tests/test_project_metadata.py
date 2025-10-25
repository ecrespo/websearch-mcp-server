import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_contains_expected_fields():
    content = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    # Basic presence checks that don't require tomllib
    assert "[project]" in content
    assert 'name = "websearch-mcp-server"' in content
    assert 'requires-python = ">=3.13"' in content
    # Make sure core dependencies appear
    assert 'loguru' in content
    assert 'mcp[cli]' in content
    assert 'python-decouple' in content
    assert 'tavily-python' in content


def test_server_exposes_web_search_tool():
    server_code = (ROOT / "server.py").read_text(encoding="utf-8")
    tree = ast.parse(server_code)
    func_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    assert "web_search" in func_names, "server.py should define a web_search function/tool"
