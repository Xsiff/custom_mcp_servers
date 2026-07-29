"""Command-line interface for direct MCP launches and the LAN gateway."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence

from .config import load_config
from .gateway import run_gateway
from .servers import discover, find


def build_parser() -> argparse.ArgumentParser:
    specs = discover()
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
    servers.add_argument(
        "--server",
        choices=[spec.name for spec in specs],
        help="direct-launch one discovered server by name",
    )
    for spec in specs:
        servers.add_argument(
            *spec.flags,
            action="store_const",
            const=spec.name,
            dest="server",
            help=spec.description,
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
    spec = find(arguments.server)
    if spec is None:
        parser.error(f"unknown server: {arguments.server}")
    try:
        return spec.build_command(
            arguments.host,
            arguments.port,
            arguments.allowed_host,
            arguments.allowed_origin,
        )
    except ValueError as error:
        parser.error(str(error))


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
