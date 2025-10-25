### Project Development Guidelines

This document captures project-specific practices and gotchas to accelerate development and troubleshooting for `websearch-mcp-server`.

---

#### Build and Configuration

- Runtime and tooling
  - Python: requires `>= 3.13` (see `pyproject.toml`).
  - Dependencies: declared in `pyproject.toml` (`httpx`, `loguru`, `mcp[cli]`, `python-decouple`, `rich`, `tavily-python`).
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
    python -m pip install loguru mcp[cli] python-decouple rich tavily-python httpx
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

#### Using the included MCP HTTP client

- A simple HTTP client is provided at `mcp_client_websearch.py`. It uses the Streamable HTTP transport and sets the required `mcp-session-id` header automatically.

- Quick start:
  1) Start the server in a terminal:
     ```bash
     python server.py
     ```
  2) In another terminal, run the client:
     ```bash
     python mcp_client_websearch.py
     ```
     By default, it connects to `127.0.0.1:9000` and issues a sample `web_search` request.

- Customizing host/port:
  - Edit the `if __name__ == "__main__":` block in `mcp_client_websearch.py`:
    ```python
    client = MCPClient(server_host="127.0.0.1", server_port=9000)
    ```
  - Or import `MCPClient` from the module and use it programmatically in your own scripts.

- Troubleshooting:
  - Ensure the server is running and reachable.
  - The client requires `httpx`; install it if not present.
  - Check logs in `logs/app.log` for server-side errors.

#### Using with Claude Desktop

You can connect Claude Desktop to this MCP server over the Streamable HTTP transport.

1) Start the server (ensure your `.env` has `tavily_api`):

```bash
python server.py
```

2) Edit Claude Desktop's config file (per OS):

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

3) Add an MCP server entry:

```json
{
  "mcpServers": {
    "websearch": {
      "type": "http",
      "transport": "streamable-http",
      "url": "http://127.0.0.1:9000",
      "description": "Local WebSearch MCP server (Tavily-backed)"
    }
  }
}
```

Notes:
- Claude Desktop 0.7+ supports `streamable-http` and automatically sets the required `mcp-session-id` header.
- If you changed the host/port in `server.py`, update the `url` accordingly.
- The server binds to `0.0.0.0:9000` by default; you can change it in `server.py`.

4) Restart Claude Desktop and verify the `websearch` tool appears under Settings ➜ Tools (or MCP Servers). In a new chat, Claude should call `web_search` when relevant.

Troubleshooting:
- Ensure the server is running and reachable at the configured URL.
- Verify `tavily_api` is set (see Local configuration).
- Check `logs/app.log` for server-side errors.
- Firewalls/VPNs can block localhost ports; allow or change the port.

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
  - Verified commands:
    ```bash
    python tests/test_temp_unittest_demo.py -v
    python tests/test_demo_sample.py -v
    python tests/test_project_metadata.py -v
    ```
    These execute simple smoke/metadata tests that check the repository README and confirm `server.py` defines the `web_search` tool.

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
  python -m pip install loguru mcp[cli] python-decouple rich tavily-python httpx
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
