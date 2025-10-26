# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.

## [0.2.0] - 2025-10-25

### Added
- Async HTTP client for the MCP server (`mcp_client_websearch.py`) with demo and JSON‑RPC helpers to list/call tools over HTTP ([9bd4ed2](https://github.com/ecrespo/websearch-mcp-server/commit/9bd4ed2)).
- Dependency: add `httpx` for the client, and guidance on programmatic usage ([9bd4ed2](https://github.com/ecrespo/websearch-mcp-server/commit/9bd4ed2)).
- Documentation: Claude Desktop configuration examples using the `streamable-http` transport in README ([9bd4ed2](https://github.com/ecrespo/websearch-mcp-server/commit/9bd4ed2)).

### Changed
- Dependency lockfile: expanded `uv.lock` with additional dependencies for enhanced functionality and reproducible installs ([947e473](https://github.com/ecrespo/websearch-mcp-server/commit/947e473)).

> SemVer: minor release (new functionality added without breaking changes).

## [0.1.0] - 2025-10-25

### Added
- Initial project setup: FastAPI MCP server with Auth0 Client Credentials auth, Tavily‑backed `web_search` tool, JSON‑RPC endpoints, SSE session channel, and session management ([94009ab](https://github.com/ecrespo/websearch-mcp-server/commit/94009ab)).
- Configuration and logging: env‑driven settings (`config.py`), Loguru + Rich logging (`logger.py`), and basic tests scaffolding ([94009ab](https://github.com/ecrespo/websearch-mcp-server/commit/94009ab)).
