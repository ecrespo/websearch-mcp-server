import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_not_empty():
    readme = ROOT / "README.md"
    assert readme.exists(), "README.md should exist"
    content = readme.read_text(encoding="utf-8").strip()
    assert len(content) > 0, "README.md should not be empty"


def test_server_defines_web_search():
    server_code = (ROOT / "server.py").read_text(encoding="utf-8")
    tree = ast.parse(server_code)
    func_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    assert "web_search" in func_names
