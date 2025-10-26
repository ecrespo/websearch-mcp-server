# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.

## [1.0.0] - 2025-10-26

### Changed
- **BREAKING**: Replaced Auth0 authentication with local token system. Authentication now uses a simple `LOCAL_TOKEN` stored in `.env` instead of Auth0 Client Credentials flow.
- Simplified `auth.py`: replaced `Auth0Client` and `Auth0Validator` with `LocalTokenClient` and `LocalTokenValidator`.
- Updated `config.py`: removed Auth0-related configuration variables (`AUTH0_DOMAIN`, `AUTH0_CLIENT_ID`, `AUTH0_CLIENT_SECRET`, `AUTH0_AUDIENCE`, `AUTH0_ALGORITHM`) and added `LOCAL_TOKEN`.
- Updated authentication flow: `authenticate` tool now returns the local token instead of fetching from Auth0.
- Updated `validate_token` tool to perform simple string comparison instead of JWT validation.

### Removed
- Dependency: removed `authlib` (no longer needed for local token authentication).
- Auth0 integration: all Auth0-specific code and configuration removed.

### Added
- Token generation guide: documentation now includes command to generate secure tokens using Python's `secrets` module.

### Migration Guide
- Remove all `AUTH0_*` variables from your `.env` file.
- Generate a secure token: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- Add `LOCAL_TOKEN=<your_generated_token>` to your `.env` file.
- Update dependencies: remove `authlib` if manually installed.

> SemVer: major release (breaking changes to authentication system).

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
