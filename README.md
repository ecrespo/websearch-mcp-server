# websearch-mcp-server

A minimal Model Context Protocol (MCP) server that exposes a `web_search` tool backed by the Tavily Search API. The server runs over the `streamable-http` transport and is suitable for use with MCP-compatible clients and inspectors.

> Note: This project emphasizes simplicity and local configurability. Network access to Tavily is required at runtime for real searches. Tests avoid network I/O.

## Overview

- Language/runtime: Python (>= 3.13)
- Transport: MCP `streamable-http`
- Entry point: `server.py`
- Core tool: `web_search(query: str) -> List[Dict]` returning Tavily results
- Logging: central Loguru configuration via `loguru_config.py` (console + rotating file)
- Config: environment-driven via `python-decouple` in `config.py`

## Requirements

- Python >= 3.13
- Dependencies (declared in `pyproject.toml`):
  - `loguru`
  - `mcp[cli]`
  - `python-decouple`
  - `rich`
  - `tavily-python`
- Optional tooling: `uv` is supported (lockfile `uv.lock` present) for reproducible installs.

## Installation

You can install dependencies with either `uv` (preferred if available) or `pip`.

### Using uv

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
python -m pip install loguru mcp[cli] python-decouple rich tavily-python
```

## Configuration

Secrets and configuration are loaded with `python-decouple`. The module `config.py` requires `tavily_api` at import time. If it is missing, importing `config.py` (and thus `server.py`) will raise.

1) Create a `.env` file at the project root (or set the environment variable directly):

```dotenv
# .env
tavily_api=YOUR_TAVILY_API_KEY
```

2) Optional logging overrides (defaults in parentheses):

- `LOG_DIR` (default: `logs`)
- `LOG_FILE` (default: `logs/app.log`)
- `LOG_LEVEL` (default: `INFO`)

## Running the Server

The MCP server is defined in `server.py` and uses the `streamable-http` transport. Default bind: `0.0.0.0:9000`.

```bash
# Ensure .env contains tavily_api (or export tavily_api in env)
python server.py
```

To connect, use an MCP client or inspector that supports `streamable-http`. See the `mcp[cli]` documentation for details on connecting to an existing endpoint.

> Security note: The server binds to `0.0.0.0` by default. Consider firewall rules or changing the host if exposing beyond localhost.

## Using with Claude Desktop

You can use this MCP server directly from Claude Desktop via the Streamable HTTP transport.

1) Start the server (ensure your `.env` has `tavily_api`):

```bash
python server.py
```

2) Create or edit Claude Desktop's config file at the following path for your OS:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

3) Add an MCP server entry pointing to this server:

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

4) Restart Claude Desktop. Then open Settings ➜ Tools (or MCP Servers) to verify `websearch` is listed. In a new chat, Claude should be able to call the `web_search` tool when relevant.

Troubleshooting:
- Ensure the server is running and reachable at the configured URL.
- Verify `tavily_api` is set (see Configuration above).
- Check `logs/app.log` for server-side errors.
- Firewalls/VPNs can block localhost ports; allow or switch to a different port.

## Scripts and Entry Points

- Application entry point: `server.py`
- No additional console scripts are defined in `pyproject.toml`.

Common commands:

- Start server: `python server.py`
- Tail logs: view `logs/app.log` (rotates daily, 31-day retention)

## Environment Variables

Required:

- `tavily_api` — Tavily API key (used by `config.py` and `TavilyClient`).

Optional (logging):

- `LOG_DIR` — directory for logs, default `logs`
- `LOG_FILE` — log file path, default `logs/app.log`
- `LOG_LEVEL` — log level, default `INFO`

## Testing

The project uses Python's built-in `unittest` for simple structural checks. Tests avoid real network/API calls.

Discovery tip: In some environments, default `unittest` discovery from the repo root may not find tests unless `tests/` is a package. Reliable ways to run tests:

1) Run a test module directly (works now):

```bash
python tests/test_temp_unittest_demo.py -v
```

2) Alternatively, make `tests/` a package (add `tests/__init__.py`) and then use discovery:

```bash
python -m unittest discover -s tests -t . -p "test*.py" -v
```

Testing notes:

- If a test imports `config.py` or `server.py`, ensure `tavily_api` is set. For pure unit tests, prefer setting a dummy value in-process before import:

```python
import os
os.environ["tavily_api"] = "dummy"

import config
import server
```

- To mock Tavily behavior without network I/O:

```python
from unittest.mock import patch

@patch("server.TavilyClient")
def test_web_search_mocked(client_cls):
    client = client_cls.return_value
    client.search.return_value = {"results": [{"title": "ok"}]}
    from server import web_search
    assert web_search("query") == [{"title": "ok"}]
```

## Project Structure

```
websearch-mcp-server/
├─ README.md
├─ config.py
├─ loguru_config.py
├─ pyproject.toml
├─ server.py
├─ tests/
│  ├─ test_demo_sample.py
│  ├─ test_project_metadata.py
│  └─ test_temp_unittest_demo.py
├─ uv.lock
└─ logs/
   └─ app.log
```

Notes:
- `logs/app.log` is where file logs are written (daily rotation, 31-day retention). Ensure the `logs/` directory is writable.

## Troubleshooting

- ImportError for `decouple` or `loguru`: dependencies not installed — re-run the install step.
- Errors on startup referencing Tavily: ensure `tavily_api` is correctly set (non-empty).
- Test discovery issues: run test modules directly or add `tests/__init__.py` and use `-t .` with discovery.

## License

TODO: No license file is present. Choose and add a LICENSE (e.g., MIT, Apache-2.0) to clarify usage and contributions.

## Acknowledgments

- Tavily Search API for web results
- `mcp` project for the server framework and CLI tooling
