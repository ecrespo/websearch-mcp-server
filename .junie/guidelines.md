### Project Development Guidelines

This document captures project-specific practices and gotchas to accelerate development and troubleshooting for `websearch-mcp-server`.

---

#### Build and Configuration

- Runtime and tooling
  - Python: requires `>= 3.13` (see `pyproject.toml`).
  - Dependencies: declared in `pyproject.toml` (`loguru`, `mcp[cli]`, `python-decouple`, `rich`, `tavily-python`).
  - Optional: `uv` is present (`uv.lock`). If available, prefer `uv` for reproducible, fast installs.

- Environment configuration
  - Secrets and config are loaded via `python-decouple`. The module `config.py` requires `tavily_api` at import time:
    - `.env` (project root) or the OS environment must define `tavily_api`.
    - Example file: `.env.example`.
  - If `tavily_api` is missing, importing `config.py` (and any module that imports it, e.g., `server.py`) will raise.

- Install
  - Using uv (preferred if available):
    ```bash
    uv venv -p 3.13
    source .venv/bin/activate
    uv sync
    ```
  - Using pip:
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    python -m pip install -U pip
    python -m pip install loguru mcp[cli] python-decouple rich tavily-python
    ```

- Local configuration
  - Create `.env` at the project root before running anything that imports `config.py`:
    ```dotenv
    tavily_api=YOUR_TAVILY_API_KEY
    ```

- Running the server
  - The MCP server is defined in `server.py` and uses the `streamable-http` transport.
  - Host/port defaults: `0.0.0.0:9000`.
  - Start:
    ```bash
    # Ensure .env contains tavily_api (or export tavily_api in env)
    python server.py
    ```
  - Connect using your MCP client/inspector of choice that supports `streamable-http`. See the `mcp[cli]` docs for details on connecting to a running endpoint.

- Logging
  - Centralized via `loguru_config.py`.
  - Console output is rich-styled; file logs are written to `logs/app.log` with daily rotation and 31-day retention.
  - Optional env overrides:
    - `LOG_DIR` (default: `logs`)
    - `LOG_FILE` (default: `logs/app.log`)
    - `LOG_LEVEL` (default: `INFO`)

---

#### Testing: How to Configure and Run

- Test framework
  - The project uses Python’s built-in `unittest` for simple structural checks.
  - Tests avoid network and external API calls. Prefer AST/static analysis or mocks.

- Discovery note (important)
  - Out of the box, default `unittest` discovery from the repo root did not find tests in this environment without packaging the `tests/` directory. Two reliable ways to run tests are:
    1) Run a test module directly with Python (works now):
       ```bash
       python tests/test_temp_unittest_demo.py -v
       ```
    2) Make `tests/` a package (add `tests/__init__.py`) and use discovery (not applied by default to keep the repo minimal). If you add `tests/__init__.py`, you can run:
       ```bash
       python -m unittest discover -s tests -t . -p "test*.py" -v
       ```

- Running existing tests (validated)
  - Verified in this session:
    ```bash
    python tests/test_temp_unittest_demo.py -v
    ```
    This executes simple smoke tests that check the repository README and confirm `server.py` defines the `web_search` tool.

- Adding new tests
  - Keep tests pure and fast; avoid real Tavily calls.
  - If a test imports `config.py` or `server.py`, ensure `tavily_api` is present during the test. For pure unit tests, prefer setting a dummy value in-process before import to avoid reading your real secrets:
    ```python
    import os
    os.environ["tavily_api"] = "dummy"

    # Now it is safe to import modules that require config
    import config
    import server
    ```
  - Example: testing the MCP tool registration without performing network I/O:
    ```python
    import ast
    from pathlib import Path

    ROOT = Path(__file__).resolve().parents[1]

    def test_server_exposes_web_search_tool():
        code = (ROOT / "server.py").read_text(encoding="utf-8")
        tree = ast.parse(code)
        func_names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        assert "web_search" in func_names
    ```
  - If you need to test behavior that touches `TavilyClient`, patch it:
    ```python
    from unittest.mock import patch

    @patch("server.TavilyClient")
    def test_web_search_mocked(client_cls):
        client = client_cls.return_value
        client.search.return_value = {"results": [{"title": "ok"}]}
        from server import web_search
        assert web_search("query") == [{"title": "ok"}]
    ```

---

#### Additional Development Information

- Code style and patterns
  - Use type hints and keep function docs concise and practical.
  - Follow the existing import order and spacing; keep logging consistent via `loguru_config.logger`.
  - Avoid network calls in unit tests; test structure, parsing, and error paths via mocks.

- Operational notes
  - `server.py` imports `config.py` at module import time. This means missing `tavily_api` will crash on import. Set `tavily_api` in `.env` (or `os.environ`) before importing or running.
  - Logging rotates daily; verify `logs/` is writable in your environment.

- Troubleshooting
  - ImportError for `decouple` or `loguru`: dependencies not installed. Re-run the install step.
  - ImportError on tests discovery like "Start directory is not importable": either run the module directly (simplest) or add `tests/__init__.py` and use `-t .` with `discover`.
  - Runtime errors on startup referencing Tavily: ensure `tavily_api` is correctly set and not empty.

---

#### Quick Reference

- Install (pip):
  ```bash
  python -m venv .venv && source .venv/bin/activate
  python -m pip install -U pip
  python -m pip install loguru mcp[cli] python-decouple rich tavily-python
  ```
- Configure env:
  ```bash
  cp .env.example .env
  # edit .env and set: tavily_api=YOUR_TAVILY_API_KEY
  ```
- Run server:
  ```bash
  python server.py
  ```
- Run tests (validated):
  ```bash
  python tests/test_temp_unittest_demo.py -v
  ```
