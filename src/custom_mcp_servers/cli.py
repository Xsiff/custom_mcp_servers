"""Command-line launcher for the example MCP servers."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence

SERVER_COMMANDS: dict[str, tuple[str, ...]] = {
    "duckduckgo": ("uvx", "duckduckgo-mcp-server"),
    "time": ("uvx", "--with", "mcp<2", "mcp-server-time"),
    "fetch": ("uvx", "--with", "mcp<2", "mcp-server-fetch"),
}


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line parser."""
    parser = argparse.ArgumentParser(
        description="Launch one of the example MCP servers over stdio."
    )
    servers = parser.add_mutually_exclusive_group()
    servers.add_argument(
        "--duckduckgo-mcp-server",
        "--duckduckgo",
        action="store_const",
        const="duckduckgo",
        dest="server",
        help="launch the DuckDuckGo search MCP server",
    )
    servers.add_argument(
        "--mcp-server-time",
        "--time",
        action="store_const",
        const="time",
        dest="server",
        help="launch the time MCP server",
    )
    servers.add_argument(
        "--mcp-server-fetch",
        "--fetch",
        action="store_const",
        const="fetch",
        dest="server",
        help="launch the fetch MCP server",
    )
    parser.add_argument(
        "--host",
        help="host for the HTTP server (for example, 0.0.0.0 for your LAN)",
    )
    parser.add_argument(
        "--port",
        type=int,
        help="port for the HTTP server",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Parse arguments and launch the chosen server in place of this process."""
    parser = build_parser()
    arguments = parser.parse_args(argv)
    if arguments.server is None:
        parser.print_help()
        return

    if (arguments.host is None) != (arguments.port is None):
        parser.error("--host and --port must be supplied together")

    command = list(SERVER_COMMANDS[arguments.server])
    if arguments.host is not None:
        if arguments.server == "duckduckgo":
            command.extend(
                [
                    "--transport",
                    "streamable-http",
                    "--host",
                    arguments.host,
                    "--port",
                    str(arguments.port),
                ]
            )
        else:
            command = [
                "uvx",
                "--with",
                "mcp<2",
                "mcp-proxy",
                "--host",
                arguments.host,
                "--port",
                str(arguments.port),
                "--",
                *command,
            ]
    os.execvp(command[0], command)
