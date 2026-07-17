# custom_mcp_servers

Custom MCP servers built in this repository.

## Tooling

This repo is set up around `uv` for environment and dependency management.

### First-time setup

```bash
uv sync --dev
```

### Common commands

```bash
make fmt
make lint
make typecheck
make test
make check
```

### Layout

```text
src/custom_mcp_servers/
tests/
```

Add your server implementations under `src/custom_mcp_servers/` and keep tests in `tests/`.
