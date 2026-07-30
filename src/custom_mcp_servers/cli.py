"""Command-line interface for direct MCP launches and the LAN gateway."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence

from .config import AppConfig, GatewayConfig, ServerConfig, load_config
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
    for spec in specs:
        parser.add_argument(
            f"--server-{spec.name}",
            action="append_const",
            const=spec.name,
            dest="selected_servers",
            help=f"include {spec.name} in a shared gateway",
        )
    parser.add_argument("--host", help="direct server HTTP bind host")
    parser.add_argument("--port", type=int, help="direct server HTTP port")
    parser.add_argument(
        "--proxy-port",
        type=int,
        default=18000,
        help="local gateway-to-server proxy port (default: 18000)",
    )
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


def _selected_config(
    arguments: argparse.Namespace, parser: argparse.ArgumentParser
) -> AppConfig:
    if not arguments.selected_servers:
        parser.error("select at least one --server-<name> option")
    if arguments.host is None or arguments.port is None:
        parser.error("shared server mode requires --host and --port")
    if not 1 <= arguments.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    if not 1 <= arguments.proxy_port <= 65535:
        parser.error("--proxy-port must be between 1 and 65535")
    selected = tuple(dict.fromkeys(arguments.selected_servers))
    specs = {spec.name: spec for spec in discover()}
    return AppConfig(
        GatewayConfig(
            arguments.host,
            arguments.port,
            arguments.proxy_port,
            tuple(arguments.allowed_host),
            tuple(arguments.allowed_origin),
        ),
        tuple(
            ServerConfig(name, True, specs[name].command) for name in selected
        ),
    )


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    if arguments.selected_servers:
        run_gateway(_selected_config(arguments, parser))
        return
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
