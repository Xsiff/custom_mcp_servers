"""Command-line interface for direct MCP launches and the LAN gateway."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence

from .config import load_config
from .gateway import run_gateway

SERVER_COMMANDS: dict[str, tuple[str, ...]] = {
    "duckduckgo": ("uvx", "duckduckgo-mcp-server"),
    "time": ("uvx", "--with", "mcp<2", "mcp-server-time"),
    "fetch": ("uvx", "--with", "mcp<2", "mcp-server-fetch"),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Launch MCP servers or the LAN gateway."
    )
    parser.add_argument("command", nargs="?", choices=("list", "serve"))
    parser.add_argument(
        "--config",
        default="config/servers.toml",
        help="TOML configuration path",
    )
    servers = parser.add_mutually_exclusive_group()
    for flag, name, help_text in (
        ("--duckduckgo-mcp-server", "duckduckgo", "launch DuckDuckGo"),
        ("--mcp-server-time", "time", "launch time"),
        ("--mcp-server-fetch", "fetch", "launch fetch"),
    ):
        aliases = {
            "duckduckgo": ["--duckduckgo"],
            "time": ["--time"],
            "fetch": ["--fetch"],
        }[name]
        servers.add_argument(
            flag,
            *aliases,
            action="store_const",
            const=name,
            dest="server",
            help=help_text,
        )
    parser.add_argument("--host", help="direct server HTTP bind host")
    parser.add_argument("--port", type=int, help="direct server HTTP port")
    parser.add_argument(
        "--allowed-host", action="append", default=[], metavar="HOST[:PORT]"
    )
    parser.add_argument(
        "--allowed-origin", action="append", default=[], metavar="ORIGIN"
    )
    return parser


def _direct_command(
    arguments: argparse.Namespace, parser: argparse.ArgumentParser
) -> list[str]:
    if arguments.server is None:
        parser.error("choose list, serve, or one direct server flag")
    if (arguments.host is None) != (arguments.port is None):
        parser.error("--host and --port must be supplied together")
    if arguments.allowed_host and arguments.server != "duckduckgo":
        parser.error("--allowed-host is only available for DuckDuckGo")
    if arguments.allowed_origin and arguments.server != "duckduckgo":
        parser.error("--allowed-origin is only available for DuckDuckGo")
    if (
        arguments.allowed_host or arguments.allowed_origin
    ) and arguments.host is None:
        parser.error("allowed host/origin requires --host and --port")
    command = list(SERVER_COMMANDS[arguments.server])
    if arguments.host is None:
        return command
    if arguments.server == "duckduckgo":
        command += [
            "--transport",
            "streamable-http",
            "--host",
            arguments.host,
            "--port",
            str(arguments.port),
        ]
        if arguments.allowed_host:
            command += ["--allowed-hosts", *arguments.allowed_host]
        if arguments.allowed_origin:
            command += ["--allowed-origins", *arguments.allowed_origin]
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
    return command


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    if arguments.command in {"list", "serve"}:
        try:
            config = load_config(arguments.config)
        except ValueError as error:
            parser.error(str(error))
        if arguments.command == "list":
            for server in config.servers:
                if server.enabled:
                    print(f"{server.name}: {' '.join(server.command)}")
                    print(f"  {config.endpoint_url(server)}")
            return
        run_gateway(config)
        return
    if arguments.server is None:
        parser.print_help()
        return
    os.execvp((_command := _direct_command(arguments, parser))[0], _command)
