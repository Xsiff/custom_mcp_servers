"""Shared direct HTTP adapter for stdio MCP servers."""

from __future__ import annotations


def make_http_command(command: tuple[str, ...]):
    """Create direct-launch behavior for a particular stdio command."""

    def build_http_command(
        host: str | None,
        port: int | None,
        allowed_hosts: list[str],
        allowed_origins: list[str],
    ) -> list[str]:
        if host is None or port is None:
            if allowed_hosts or allowed_origins:
                raise ValueError("HTTP allow-lists require --host and --port")
            return list(command)
        if allowed_hosts or allowed_origins:
            raise ValueError(
                "this stdio server does not support direct allow-lists"
            )
        return [
            "uvx",
            "--with",
            "mcp<2",
            "mcp-proxy",
            "--host",
            host,
            "--port",
            str(port),
            "--",
            *command,
        ]

    return build_http_command
