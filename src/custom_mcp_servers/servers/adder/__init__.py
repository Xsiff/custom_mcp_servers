"""In-repository adder MCP server and its launcher metadata."""

from __future__ import annotations

from ...server_spec import ServerSpec
from ...stdio import make_http_command

COMMAND = (
    "uv",
    "run",
    "--project",
    ".",
    "--no-sync",
    "--with",
    "mcp==1.29.0",
    "python",
    "-m",
    "custom_mcp_servers.servers.adder.server",
)


SPEC = ServerSpec(
    name="adder",
    command=COMMAND,
    flags=("--adder",),
    description="launch the in-repository adder server",
    command_builder=make_http_command(COMMAND),
)
