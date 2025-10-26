# websearch-mcp-server

A Model Context Protocol (MCP) server that provides authenticated web search via Tavily. The server is built with FastAPI, speaks JSON-RPC 2.0 over the `streamable-http` transport (SSE + HTTP), and is suitable for use with MCP-compatible clients such as Claude Desktop.

Note:
- This project emphasizes simplicity and local configurability.
- Network access to Tavily is required at runtime for real searches.
- Tests avoid network I/O and use mocks or static checks.

## Overview

- Language/runtime: Python (>= 3.13)
- Transport: MCP `streamable-http`
- Entry point: `server.py`
- Core tools (registered by the server):
  - `authenticate` — authenticates the session using the local token configured in the server.
  - `web_search` — queries Tavily; requires prior authentication.
  - `validate_token` — validates a given token against the local token stored in configuration.
- Logging: centralized via `logger.py` (Loguru + Rich)
- Config: environment-driven via `python-decouple` in `config.py`

## Requirements

- Python >= 3.13
- Dependencies (declared in `pyproject.toml`):
  - `fastapi`, `httpx`, `loguru`, `mcp[cli]`, `python-decouple`, `rich`, `sse-starlette`, `tavily-python`, `uvicorn[standard]`
- Optional tooling: `uv` is supported (lockfile `uv.lock` present) for reproducible installs.

## Installation

Install with either `uv` (preferred if available) or `pip`.

### Using uv (preferred)

```bash
uv venv -p 3.13
source .venv/bin/activate
uv sync
```

### Using pip

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install fastapi httpx loguru "mcp[cli]" python-decouple rich sse-starlette tavily-python "uvicorn[standard]"
```

## Configuration

Secrets and configuration are loaded via `python-decouple` in `config.py`. Required variables are validated at startup (during app lifespan init). If required variables are missing, the server will log and raise.

Required at startup:
- `LOCAL_TOKEN` — a secure token for authentication (generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`)
- `TAVILY_API_KEY`

Useful optional settings with defaults:
- `MCP_SERVER_HOST` (default: `0.0.0.0`)
- `MCP_SERVER_PORT` (default: `8000`)
- `LOG_LEVEL` (default: `INFO`), `LOG_FILE` (default: `logs/mcp_server.log`)
- `LOG_ROTATION` (default: `10 MB`), `LOG_RETENTION` (default: `7 days`)
- `SESSION_TIMEOUT` (default: `3600` seconds), `SESSION_CLEANUP_INTERVAL` (default: `300` seconds)

Example `.env` (project root):

```dotenv
# Local Token Configuration
LOCAL_TOKEN=your_generated_secure_token_here

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

## Logging

Logging is configured centrally in `logger.py` using Loguru + Rich. Console output is rich-styled; file logs go to `logs/mcp_server.log` with rotation/retention from env. Errors are additionally captured in `logs/errors.log`.

## Running the Server

The server uses FastAPI and exposes endpoints for MCP over HTTP+SSE.

Default bind: `MCP_SERVER_HOST:MCP_SERVER_PORT` → `0.0.0.0:8000`.

```bash
# Ensure required env vars are set (see .env example above)
python server.py
```

Key endpoints:
- `GET /health` — basic health info
- `GET /sse/{session_id}` — Server-Sent Events (heartbeats and connect event)
- `POST /mcp/{session_id}` — JSON-RPC 2.0 for MCP methods:
  - `tools/list` → returns available tools
  - `tools/call` with params `{ name, arguments }`

## Available MCP tools

- `authenticate` — authenticates the session using the local token configured in the server and stores it in the session.
- `web_search` — queries Tavily; requires prior authentication.
  - Arguments: `query: str` (required), `max_results: int = 5`, `search_depth: "basic"|"advanced" = "basic"`
- `validate_token` — validates a given token against the local token stored in configuration.

## Using the included MCP HTTP client

A simple async MCP HTTP client is provided at `mcp_client_websearch.py`.

Quick start:

1) Start the server:

```bash
python server.py
```

2) In another terminal, run the client demo:

```bash
python mcp_client_websearch.py
```

It will perform: health check → list tools → authenticate → sample `web_search` → delete session.

Customize programmatically:

```python
from mcp_client_websearch import MCPClientHTTP

client = MCPClientHTTP(base_url="http://127.0.0.1:8000", session_id="my-session")
# await client.list_tools(), client.call_tool("authenticate"), etc.
```

Notes:
- The client speaks JSON-RPC to `POST /mcp/{session_id}` and uses the session endpoints for status and cleanup.
- Ensure `httpx` is installed (included in dependencies).

## Using with Claude Desktop

You can connect Claude Desktop to this MCP server over the Streamable HTTP transport. The server uses a local token authentication system that is handled entirely server-side for security.

### Setup Instructions

1) **Configure your server environment**

Ensure your `.env` file has the required settings (see Configuration section above):
- `LOCAL_TOKEN` — the secure authentication token (generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`)
- `TAVILY_API_KEY` — your Tavily API key

2) **Start the server**

```bash
python server.py
```

3) **Configure Claude Desktop**

Edit Claude Desktop's config file (location depends on your OS):

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

Add an MCP server entry:

```json
{
  "mcpServers": {
    "websearch": {
      "type": "http",
      "transport": "streamable-http",
      "url": "http://127.0.0.1:8000",
      "description": "Local WebSearch MCP server with Tavily and local token authentication"
    }
  }
}
```

**Important notes:**
- You do NOT need to provide the `LOCAL_TOKEN` in the Claude Desktop configuration
- The token is stored securely in the server's `.env` file and never exposed to clients
- Authentication is handled through the `authenticate` tool call

4) **Restart Claude Desktop**

After saving the configuration, restart Claude Desktop to load the new MCP server.

### Usage Workflow

Once Claude Desktop is connected to the server, follow this workflow:

**Step 1: Authenticate the session**

The first time you want to use web search in a conversation, you must authenticate:

- Ask Claude: **"Please authenticate using the authenticate tool"** or **"Run the authenticate tool"**
- Alternatively, use the Tools panel in Claude Desktop to manually execute the `authenticate` tool
- **No arguments are required** — the server automatically uses the `LOCAL_TOKEN` from its configuration

On success, you'll see:
```
✅ Autenticación exitosa!

Token local válido.
Tipo: local_token
```

**Step 2: Use web search**

After authentication, you can use the `web_search` tool:

- Ask in natural language: **"Search the web for the latest Python FastAPI tutorials"**
- Or explicitly: **"Use web_search to find information about MCP servers, limit to 5 results"**
- Claude will automatically call `web_search` with appropriate parameters

Example arguments for `web_search`:
- `query` (required): search query string
- `max_results` (optional, default: 5): number of results to return
- `search_depth` (optional, default: "basic"): either "basic" or "advanced"

### How Authentication Works

This server implements a simplified local token authentication system:

1. The `LOCAL_TOKEN` is stored in the server's `.env` file (server-side only)
2. When you call the `authenticate` tool (with no arguments), the server:
   - Retrieves the `LOCAL_TOKEN` from its configuration
   - Validates the token internally
   - Stores the authentication state in your session
3. The actual token value is never sent to or required from the client
4. Once authenticated, your session can use `web_search` until it expires (default: 1 hour)

### Additional Tools

- **`validate_token`**: Manually validate a token string (requires `token` argument). Useful for testing.

### Technical Notes

- Claude Desktop 0.7+ supports `streamable-http` and automatically manages session IDs via the `mcp-session-id` header
- The server organizes requests by `{session_id}` in the URL path (e.g., `POST /mcp/{session_id}`)
- If you changed `MCP_SERVER_HOST` or `MCP_SERVER_PORT` in your `.env`, update the `url` in Claude Desktop config accordingly
- Sessions expire after `SESSION_TIMEOUT` seconds (default: 3600 = 1 hour)

### Troubleshooting

**Authentication errors:**
- **Error: "Debe autenticarse primero"** → You haven't called the `authenticate` tool yet. Run it first before using `web_search`.
- **Error: "No se pudo obtener token local"** → The server's `LOCAL_TOKEN` is not configured in `.env`. Check your environment variables.
- **Error: "Token obtenido pero no es válido"** → The `LOCAL_TOKEN` format is invalid. Regenerate it using the command from the Configuration section.

**Connection errors:**
- **Claude Desktop doesn't see the server** → Verify the server is running (`python server.py`) and the URL in the config matches your `MCP_SERVER_HOST:MCP_SERVER_PORT`.
- **404 errors** → Check that you're using the correct URL format (`http://127.0.0.1:8000` or `http://localhost:8000`).

**Search errors:**
- **Tavily API errors** → Verify `TAVILY_API_KEY` is set correctly and you have network connectivity.
- **Empty results** → Try a different query or increase `max_results`.

**Session issues:**
- **Authentication lost** → Sessions expire after `SESSION_TIMEOUT`. Simply run `authenticate` again.
- **Stale session** → Delete and recreate by restarting Claude Desktop or waiting for automatic cleanup.

## Testing

- Test framework: Python’s built-in `unittest` for simple structural checks and metadata verification.
- Tests avoid network and external API calls. Prefer AST/static analysis or mocks.

Running existing tests:

```bash
python tests/test_temp_unittest_demo.py -v
python tests/test_demo_sample.py -v
python tests/test_project_metadata.py -v
```

Tips for writing tests:

- Keep tests pure and fast; avoid real Tavily calls.
- If a test imports `config.py` or `server.py`, set required env values in-process before import to avoid using real secrets:

```python
import os
os.environ["LOCAL_TOKEN"] = "test-token-dummy"
os.environ["TAVILY_API_KEY"] = "dummy"

import config  # safe after env vars are set
import server
```

- To test behavior that touches `TavilyClient`, patch it:

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

## Quick Reference

- Install (pip):

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install -U pip
python -m pip install fastapi httpx loguru "mcp[cli]" python-decouple rich sse-starlette tavily-python "uvicorn[standard]"
```

- Configure env: create `.env` with required settings (see example above)
- Run server: `python server.py`
- Try the client demo: `python mcp_client_websearch.py`
- Sample manual MCP call (tools/list):

```bash
curl -s http://127.0.0.1:8000/mcp/demo-session \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

## Project Structure

```
websearch-mcp-server/
├─ README.md
├─ auth.py
├─ config.py
├─ logger.py
├─ mcp_client_websearch.py
├─ pyproject.toml
├─ server.py
├─ tests/
│  ├─ test_demo_sample.py
│  ├─ test_project_metadata.py
│  └─ test_temp_unittest_demo.py
├─ uv.lock
└─ logs/
   ├─ app.log
   ├─ errors.log
   └─ mcp_server.log
```

## Troubleshooting

- ImportError for `fastapi`, `loguru`, etc.: dependencies not installed — re-run the install step.
- 401/permission issues when calling `web_search`: ensure you called the `authenticate` tool first and that LOCAL_TOKEN is correctly configured.
- 404 for `/session/{id}/status`: session not yet created; it is created on first `/mcp/{id}` or `/sse/{id}` call.
- Tavily-related errors: verify `TAVILY_API_KEY` and network connectivity.

## License

TODO: No license file is present. Choose and add a LICENSE (e.g., MIT, Apache-2.0) to clarify usage and contributions.

## Acknowledgments

- Tavily Search API for web results
- `mcp` project for the server framework and CLI tooling
