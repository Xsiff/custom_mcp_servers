"""Fetch MCP server integration."""

from __future__ import annotations

from ..server_spec import ServerSpec
from ..stdio import make_http_command

COMMAND = ("uvx", "--with", "mcp<2", "mcp-server-fetch")


SPEC = ServerSpec(
    name="fetch",
    command=COMMAND,
    flags=("--mcp-server-fetch", "--fetch"),
    description="launch fetch",
    command_builder=make_http_command(COMMAND),
)
