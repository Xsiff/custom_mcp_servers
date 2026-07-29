"""Generic contract implemented by each locally supported MCP server."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

CommandBuilder = Callable[
    [str | None, int | None, list[str], list[str]], list[str]
]


@dataclass(frozen=True)
class ServerSpec:
    """Metadata and direct-launch behavior for one MCP server."""

    name: str
    command: tuple[str, ...]
    flags: tuple[str, ...]
    description: str
    command_builder: CommandBuilder

    def build_command(
        self,
        host: str | None,
        port: int | None,
        allowed_hosts: list[str],
        allowed_origins: list[str],
    ) -> list[str]:
        return self.command_builder(host, port, allowed_hosts, allowed_origins)
