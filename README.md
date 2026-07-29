# custom_mcp_servers

Custom MCP servers built in this repository.

## Example MCP client configuration

[`src/examples/config.json`](src/examples/config.json) is a client
configuration example, not a server implemented by this repository. Copy its
`mcpServers` object into the configuration file for your MCP client.

The `time` and `fetch` examples explicitly constrain their MCP SDK dependency
to version 1 (`mcp<2`). Their current releases still import the SDK's old
`McpError` name and therefore fail when `uvx` resolves MCP 2.x, which renamed
that symbol to `MCPError`. The constraint keeps the examples runnable until
those servers release MCP 2.x-compatible versions.

You can verify the commands outside an MCP client:

```bash
uvx --with 'mcp<2' mcp-server-time --help
uvx --with 'mcp<2' mcp-server-fetch --help
uvx duckduckgo-mcp-server --help
```

Each server communicates over standard input/output, so it will appear to wait
when launched without a client; that is expected.

### Gateway setup

Copy the committed template, then edit the ignored machine-local file:

```bash
cp config/servers.example.toml config/servers.toml
```

Set `gateway.bind_host` to `0.0.0.0` (all interfaces) or a specific interface,
set the server's LAN address in `allowed_hosts`, and add the Llama UI origin to
`allowed_origins`. The bind address controls where the process listens; clients
must use the concrete LAN IP, never `0.0.0.0`. Port-forwarding this unauthenticated
v1 gateway is unsupported.

Inspect the enabled registry without starting anything:

```bash
uv run mcp list --config config/servers.toml
```

Start the gateway:

```bash
uv run mcp serve --config config/servers.toml
```

Configure Llama with the named endpoints printed by `list`, for example:

```text
http://192.168.1.20:8000/servers/duckduckgo/mcp
http://192.168.1.20:8000/servers/time/mcp
http://192.168.1.20:8000/servers/fetch/mcp
```

To add a stdio MCP tool, add one enabled `[[servers]]` entry with a unique
name and explicit command to `config/servers.toml`; launcher code does not need
to change.

### Direct launcher command

After `uv sync --dev`, use the project's launcher to start one server:

```bash
uv run mcp --help
uv run mcp --duckduckgo-mcp-server
uv run mcp --mcp-server-time
uv run mcp --mcp-server-fetch
```

Short aliases (`--duckduckgo`, `--time`, and `--fetch`) are also available.
Only one server can run per invocation because an MCP stdio server needs
exclusive use of standard input and output.

To host a server on your LAN, supply both a host and port:

```bash
uv run mcp --duckduckgo --host 0.0.0.0 --port 8000
uv run mcp --time --host 0.0.0.0 --port 8001
uv run mcp --fetch --host 0.0.0.0 --port 8002
```

DuckDuckGo uses its native Streamable HTTP mode. Time and fetch are stdio-only
upstream, so the launcher uses an MCP 1.x-compatible local proxy to expose
them over HTTP. Do not port-forward these ports or bind them to a public host.

When DuckDuckGo is accessed through a LAN IP, explicitly allow the host header
used by the MCP client:

```bash
uv run mcp --duckduckgo --host 0.0.0.0 --port 8001 \
  --allowed-host 192.168.0.26:8001 \
  --allowed-origin http://192.168.0.12:*
```

Use the server computer's LAN address and port in `--allowed-host`; it must
match the MCP URL configured in the client. Add `--allowed-host` again for any
additional permitted host header. Use the Llama UI computer's LAN address in
`--allowed-origin`; `:*` permits any local UI port on that computer.

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
