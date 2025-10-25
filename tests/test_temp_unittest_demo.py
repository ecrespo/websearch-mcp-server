import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestRepositorySmoke(unittest.TestCase):
    def test_readme_not_empty(self):
        readme = ROOT / "README.md"
        self.assertTrue(readme.exists(), "README.md should exist")
        content = readme.read_text(encoding="utf-8").strip()
        self.assertGreater(len(content), 0, "README.md should not be empty")

    def test_server_defines_web_search(self):
        server_code = (ROOT / "server.py").read_text(encoding="utf-8")
        tree = ast.parse(server_code)
        func_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
        self.assertIn("web_search", func_names)


if __name__ == "__main__":
    unittest.main()