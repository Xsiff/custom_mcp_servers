"""Time MCP server integration."""

from __future__ import annotations

from ..server_spec import ServerSpec
from ..stdio import make_http_command

COMMAND = ("uvx", "--with", "mcp<2", "mcp-server-time")


SPEC = ServerSpec(
    name="time",
    command=COMMAND,
    flags=("--mcp-server-time", "--time"),
    description="launch time",
    command_builder=make_http_command(COMMAND),
)
