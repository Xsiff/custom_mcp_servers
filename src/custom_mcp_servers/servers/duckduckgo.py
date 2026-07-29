"""DuckDuckGo MCP server integration."""

from __future__ import annotations

from ..server_spec import ServerSpec


def build_command(
    host: str | None,
    port: int | None,
    allowed_hosts: list[str],
    allowed_origins: list[str],
) -> list[str]:
    command = ["uvx", "--with", "mcp==1.29.0", "duckduckgo-mcp-server"]
    if host is None:
        if allowed_hosts or allowed_origins:
            raise ValueError("HTTP allow-lists require --host and --port")
        return command
    if port is None:
        raise ValueError("--host and --port must be supplied together")
    command += [
        "--transport",
        "streamable-http",
        "--host",
        host,
        "--port",
        str(port),
    ]
    if allowed_hosts:
        command += ["--allowed-hosts", *allowed_hosts]
    if allowed_origins:
        command += ["--allowed-origins", *allowed_origins]
    return command


SPEC = ServerSpec(
    name="duckduckgo",
    command=("uvx", "--with", "mcp==1.29.0", "duckduckgo-mcp-server"),
    flags=("--duckduckgo-mcp-server", "--duckduckgo"),
    description="launch DuckDuckGo",
    command_builder=build_command,
)
