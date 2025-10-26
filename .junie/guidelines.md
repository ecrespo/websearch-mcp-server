### Project Development Guidelines

This document captures project-specific practices and gotchas to accelerate development and troubleshooting for `websearch-mcp-server`.

---

#### Build and Configuration

- Runtime and tooling
  - Python: requires `>= 3.13` (see `pyproject.toml`).
  - Dependencies (declared in `pyproject.toml`):
    - `authlib`, `fastapi`, `httpx`, `loguru`, `mcp[cli]`, `python-decouple`, `rich`, `sse-starlette`, `tavily-python`, `uvicorn[standard]`.
  - Optional: `uv` is present (`uv.lock`). If available, prefer `uv` for reproducible, fast installs.

- Environment configuration
  - Secrets and config are loaded via `python-decouple` in `config.py`.
  - Required at startup (validated in `settings.validate()`):
    - `AUTH0_DOMAIN`, `AUTH0_CLIENT_ID`, `AUTH0_CLIENT_SECRET`, `AUTH0_AUDIENCE`
    - `TAVILY_API_KEY`
  - Useful optional settings with defaults (see `config.py`):
    - `MCP_SERVER_HOST` (default: `0.0.0.0`)
    - `MCP_SERVER_PORT` (default: `8000`)
    - `LOG_LEVEL` (default: `INFO`), `LOG_FILE` (default: `logs/mcp_server.log`)
    - `LOG_ROTATION` (default: `10 MB`), `LOG_RETENTION` (default: `7 days`)
    - `SESSION_TIMEOUT` (default: `3600` seconds), `SESSION_CLEANUP_INTERVAL` (default: `300` seconds)
  - Example `.env` (project root):
    ```dotenv
    # Auth0
    AUTH0_DOMAIN=your-tenant.auth0.com
    AUTH0_CLIENT_ID=your_client_id
    AUTH0_CLIENT_SECRET=your_client_secret
    AUTH0_AUDIENCE=https://your.api.audience
    AUTH0_ALGORITHM=RS256

    # Tavily
    TAVILY_API_KEY=your_tavily_api_key

    # Server
    MCP_SERVER_HOST=0.0.0.0
    MCP_SERVER_PORT=8000

    # Logging
    LOG_LEVEL=INFO
    LOG_FILE=logs/mcp_server.log
    LOG_ROTATION=10 MB
    LOG_RETENTION=7 days

    # Sessions
    SESSION_TIMEOUT=3600
    SESSION_CLEANUP_INTERVAL=300
    ```
  - If required vars are missing, the server will log and raise at startup (during lifespan init).

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
    python -m pip install authlib fastapi httpx loguru "mcp[cli]" python-decouple rich sse-starlette tavily-python "uvicorn[standard]"
    ```

- Logging
  - Centralized via `logger.py` (Loguru + Rich). Console output is rich-styled; file logs go to `logs/mcp_server.log` with rotation/retention from env.
  - Errors are additionally captured in `logs/errors.log`.

---

#### Running the server

- The server is implemented with FastAPI and exposes endpoints for MCP over HTTP+SSE.
- Host/port defaults come from `config.py`: `0.0.0.0:8000`.
- Start the server:
  ```bash
  # Ensure required env vars are set (see .env example above)
  python server.py
  ```
- Key endpoints:
  - `GET /health` — basic health info
  - `GET /sse/{session_id}` — Server-Sent Events (heartbeats and connect event)
  - `POST /mcp/{session_id}` — JSON-RPC 2.0 for MCP methods:
    - `tools/list` → returns available tools
    - `tools/call` with params `{ name, arguments }`

- Available MCP tools (registered in `server.py`):
  - `authenticate` — obtains an Auth0 access token using Client Credentials and stores it in the session.
  - `web_search` — queries Tavily; requires prior authentication.
    - Arguments: `query: str` (required), `max_results: int = 5`, `search_depth: "basic"|"advanced" = "basic"`
  - `validate_token` — validates a given JWT against Auth0 JWKS.

---

#### Using the included MCP HTTP client

- A simple async HTTP client is provided at `mcp_client_websearch.py`.
- Default configuration:
  - Base URL: `http://localhost:8000`
  - Session ID: `test-session` (or `demo-session` in the demo `main()`)
- Quick start:
  1) Start the server:
     ```bash
     python server.py
     ```
  2) In another terminal, run the client demo:
     ```bash
     python mcp_client_websearch.py
     ```
     It will perform: health check → list tools → authenticate → sample `web_search` → delete session.
- Customize programmatically:
  ```python
  from mcp_client_websearch import MCPClientHTTP

  client = MCPClientHTTP(base_url="http://127.0.0.1:8000", session_id="my-session")
  # await client.list_tools(), client.call_tool("authenticate"), etc.
  ```
- Notes:
  - The client speaks JSON-RPC to `POST /mcp/{session_id}` and uses the session endpoints for status and cleanup.
  - Ensure `httpx` is installed (included in dependencies).

---

#### Using with Claude Desktop

You can connect Claude Desktop to this MCP server over the Streamable HTTP transport.

1) Start the server (ensure your `.env` has the required settings):

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
      "url": "http://127.0.0.1:8000",
      "description": "Local WebSearch MCP server (Auth0 + Tavily)"
    }
  }
}
```

Notes:
- Claude Desktop 0.7+ supports `streamable-http` and automatically sets the required `mcp-session-id` header.
- The server organizes requests by `{session_id}` in the URL path (e.g., `POST /mcp/{session_id}`); most clients will set this automatically when establishing a session.
- If you changed the host/port in `config.py`, update the `url` accordingly.

---

#### Testing: How to Configure and Run

- Test framework
  - Uses Python’s built-in `unittest` for simple structural checks and metadata verification.
  - Tests avoid network and external API calls. Prefer AST/static analysis or mocks.

- Running existing tests (validated)
  - From the repo root, execute modules directly:
    ```bash
    python tests/test_temp_unittest_demo.py -v
    python tests/test_demo_sample.py -v
    python tests/test_project_metadata.py -v
    ```

- Tips for writing tests
  - Keep tests pure and fast; avoid real Tavily or Auth0 calls.
  - If a test imports `config.py` or `server.py`, set required env values in-process before import to avoid using real secrets:
    ```python
    import os
    os.environ["AUTH0_DOMAIN"] = "example.auth0.com"
    os.environ["AUTH0_CLIENT_ID"] = "dummy"
    os.environ["AUTH0_CLIENT_SECRET"] = "dummy"
    os.environ["AUTH0_AUDIENCE"] = "https://api.example"
    os.environ["TAVILY_API_KEY"] = "dummy"

    import config  # safe after env vars are set
    import server
    ```
  - To test behavior that touches `TavilyClient` or Auth0 HTTP calls, patch them:
    ```python
    from unittest.mock import patch

    @patch("server.TavilyClient")
    def test_web_search_mocked(client_cls):
      client = client_cls.return_value
      client.search.return_value = {"results": [{"title": "ok"}]}
      # Import and exercise the web_search pathway via the server's tool call
      from server import mcp_server_instance
      import asyncio
      res = asyncio.run(mcp_server_instance.handle_tool_call(
          tool_name="web_search",
          arguments={"query": "test", "max_results": 1},
          session_id="test-session"
      ))
      assert any("ok" in item.text for item in res)
    ```

- Discovery note
  - If you prefer discovery, add `tests/__init__.py` and run:
    ```bash
    python -m unittest discover -s tests -t . -p "test*.py" -v
    ```

---

#### Additional Development Information

- Code style and patterns
  - Use type hints and keep function/method docs concise and practical.
  - Follow the existing import order and spacing; keep logging consistent via `logger` from `logger.py`.
  - Avoid network calls in unit tests; test structure, parsing, and error paths via mocks.

- Operational notes
  - `server.py` validates settings at startup; missing required env vars will stop the app before serving requests.
  - Session cleanup runs periodically; default timeout is 1 hour. Tune via env if needed.
  - SSE heartbeats are sent every ~30s while connected.

- Troubleshooting
  - ImportError for `fastapi`, `authlib`, `loguru`, etc.: dependencies not installed. Re-run the install step.
  - 401/permission issues when calling `web_search`: ensure you called the `authenticate` tool first and that Auth0 credentials are correct.
  - 404 for `/session/{id}/status`: session not yet created; it is created on first `/mcp/{id}` or `/sse/{id}` call.
  - Tavily-related errors: verify `TAVILY_API_KEY` and network connectivity.

---

#### Quick Reference

- Install (pip):
  ```bash
  python -m venv .venv && source .venv/bin/activate
  python -m pip install -U pip
  python -m pip install authlib fastapi httpx loguru "mcp[cli]" python-decouple rich sse-starlette tavily-python "uvicorn[standard]"
  ```
- Configure env:
  ```bash
  # create .env with required settings (see example above)
  ```
- Run server:
  ```bash
  python server.py
  ```
- Try the client demo:
  ```bash
  python mcp_client_websearch.py
  ```
- Sample manual MCP call (tools/list):
  ```bash
  curl -s http://127.0.0.1:8000/mcp/demo-session \
    -H 'Content-Type: application/json' \
    -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
  ```
