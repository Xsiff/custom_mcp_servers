"""Configuration loading and validation for the MCP LAN gateway."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GatewayConfig:
    bind_host: str
    port: int
    proxy_port: int
    allowed_hosts: tuple[str, ...]
    allowed_origins: tuple[str, ...]


@dataclass(frozen=True)
class ServerConfig:
    name: str
    enabled: bool
    command: tuple[str, ...]

    @property
    def endpoint_path(self) -> str:
        return f"/servers/{self.name}/mcp"


@dataclass(frozen=True)
class AppConfig:
    gateway: GatewayConfig
    servers: tuple[ServerConfig, ...]

    def endpoint_url(self, server: ServerConfig) -> str:
        return f"http://{self.gateway.bind_host}:{self.gateway.port}{server.endpoint_path}"


def _port(value: object, field: str) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or not 1 <= value <= 65535
    ):
        raise ValueError(f"{field} must be an integer between 1 and 65535")
    return value


def _strings(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ValueError(f"{field} must be a string array")
    return tuple(item for item in value if isinstance(item, str))


def load_config(path: str | Path) -> AppConfig:
    """Read, validate, and return a gateway configuration."""
    config_path = Path(path)
    try:
        with config_path.open("rb") as stream:
            raw = tomllib.load(stream)
    except FileNotFoundError as error:
        raise ValueError(
            f"configuration file not found: {config_path}"
        ) from error
    except tomllib.TOMLDecodeError as error:
        raise ValueError(f"invalid TOML in {config_path}: {error}") from error

    gateway_raw = raw.get("gateway")
    if not isinstance(gateway_raw, dict):
        raise ValueError("configuration requires a [gateway] table")
    bind_host = gateway_raw.get("bind_host")
    if not isinstance(bind_host, str) or not bind_host:
        raise ValueError("gateway.bind_host must be a non-empty string")
    gateway = GatewayConfig(
        bind_host=bind_host,
        port=_port(gateway_raw.get("port"), "gateway.port"),
        proxy_port=_port(gateway_raw.get("proxy_port"), "gateway.proxy_port"),
        allowed_hosts=_strings(
            gateway_raw.get("allowed_hosts"), "gateway.allowed_hosts"
        ),
        allowed_origins=_strings(
            gateway_raw.get("allowed_origins"), "gateway.allowed_origins"
        ),
    )
    entries = raw.get("servers")
    if not isinstance(entries, list) or not entries:
        raise ValueError(
            "configuration requires at least one [[servers]] entry"
        )
    servers: list[ServerConfig] = []
    names: set[str] = set()
    for index, entry in enumerate(entries, 1):
        if not isinstance(entry, dict):
            raise ValueError(f"servers entry {index} must be a table")
        name = entry.get("name")
        if not isinstance(name, str) or not re.fullmatch(
            r"[A-Za-z0-9_-]+", name
        ):
            raise ValueError(f"servers entry {index} has an invalid name")
        if name in names:
            raise ValueError(f"duplicate server name: {name}")
        names.add(name)
        enabled = entry.get("enabled", True)
        if not isinstance(enabled, bool):
            raise ValueError(f"servers.{name}.enabled must be a boolean")
        command = _strings(entry.get("command"), f"servers.{name}.command")
        if not command:
            raise ValueError(f"servers.{name}.command must not be empty")
        servers.append(ServerConfig(name, enabled, command))
    if not any(server.enabled for server in servers):
        raise ValueError("configuration must enable at least one server")
    return AppConfig(gateway, tuple(servers))
