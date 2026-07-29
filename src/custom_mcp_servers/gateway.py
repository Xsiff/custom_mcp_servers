"""LAN HTTP gateway for named MCP proxy endpoints."""

from __future__ import annotations

import asyncio
import contextlib
import shlex
import subprocess
from urllib.parse import urlsplit, urlunsplit

from .config import AppConfig

MCP_PROXY_VERSION = "0.8.1"


def proxy_command(config: AppConfig) -> list[str]:
    """Build the loopback-only mcp-proxy command."""
    command = [
        "uvx",
        "--with",
        "mcp<2",
        "--with",
        f"mcp-proxy=={MCP_PROXY_VERSION}",
        "mcp-proxy",
        "--host",
        "127.0.0.1",
        "--port",
        str(config.gateway.proxy_port),
    ]
    for server in config.servers:
        if server.enabled:
            command.extend(
                ["--named-server", server.name, shlex.join(server.command)]
            )
    return command


def _header_value(headers: list[tuple[str, str]], name: str) -> str | None:
    name = name.lower()
    for key, value in headers:
        if key.lower() == name:
            return value
    return None


def _response(status: int, reason: str, body: bytes) -> bytes:
    return (
        f"HTTP/1.1 {status} {reason}\r\nContent-Length: {len(body)}\r\n"
        "Content-Type: text/plain; charset=utf-8\r\nConnection: close\r\n\r\n"
    ).encode() + body


def _cors_headers(origin: str | None, requested: str | None = None) -> bytes:
    if origin is None:
        return b""
    requested_headers = (
        requested or "Content-Type, Mcp-Session-Id, Last-Event-ID"
    )
    return (
        f"Access-Control-Allow-Origin: {origin}\r\n"
        "Access-Control-Allow-Credentials: true\r\n"
        "Access-Control-Allow-Methods: GET, POST, DELETE, OPTIONS\r\n"
        f"Access-Control-Allow-Headers: {requested_headers}\r\n"
        "Access-Control-Expose-Headers: Mcp-Session-Id\r\n"
        "Vary: Origin\r\n"
    ).encode("latin-1")


class Gateway:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.proxy: subprocess.Popen[bytes] | None = None
        self.server: asyncio.AbstractServer | None = None

    async def start(self) -> None:
        self.proxy = subprocess.Popen(proxy_command(self.config))
        try:
            self.server = await asyncio.start_server(
                self._handle,
                self.config.gateway.bind_host,
                self.config.gateway.port,
            )
        except Exception:
            await self.close()
            raise

    async def close(self) -> None:
        if self.server is not None:
            self.server.close()
            await self.server.wait_closed()
        if self.proxy is not None and self.proxy.poll() is None:
            self.proxy.terminate()
            try:
                await asyncio.to_thread(self.proxy.wait, 5)
            except subprocess.TimeoutExpired:
                self.proxy.kill()
                await asyncio.to_thread(self.proxy.wait)

    async def serve_forever(self) -> None:
        await self.start()
        assert self.server is not None
        try:
            async with self.server:
                await self.server.serve_forever()
        finally:
            await self.close()

    async def _handle(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            request_line = await reader.readline()
            if not request_line:
                return
            method, path, _ = (
                request_line.decode("latin-1").rstrip("\r\n").split(" ", 2)
            )
            headers: list[tuple[str, str]] = []
            while True:
                line = await reader.readline()
                if line in (b"\r\n", b"\n", b""):
                    break
                key, value = line.decode("latin-1").rstrip("\r\n").split(":", 1)
                headers.append((key, value.strip()))
            host = _header_value(headers, "host")
            origin = _header_value(headers, "origin")
            if host not in self.config.gateway.allowed_hosts:
                writer.write(
                    _response(
                        421, "Misdirected Request", b"Host is not allowed\n"
                    )
                )
                await writer.drain()
                return
            if (
                origin is not None
                and origin not in self.config.gateway.allowed_origins
            ):
                writer.write(
                    _response(403, "Forbidden", b"Origin is not allowed\n")
                )
                await writer.drain()
                return
            public_path = urlsplit(path).path
            enabled_names = {s.name for s in self.config.servers if s.enabled}
            if not any(
                public_path == f"/servers/{name}/mcp" for name in enabled_names
            ):
                writer.write(
                    _response(404, "Not Found", b"Unknown MCP endpoint\n")
                )
                await writer.drain()
                return
            if method.upper() == "OPTIONS":
                response = (
                    b"HTTP/1.1 204 No Content\r\n"
                    + _cors_headers(
                        origin,
                        _header_value(
                            headers, "access-control-request-headers"
                        ),
                    )
                    + b"Content-Length: 0\r\nConnection: close\r\n\r\n"
                )
                writer.write(response)
                await writer.drain()
                return
            length = int(_header_value(headers, "content-length") or "0")
            body = await reader.readexactly(length) if length else b""
            await self._forward(method, path, headers, body, writer)
        except (ValueError, asyncio.IncompleteReadError):
            writer.write(
                _response(400, "Bad Request", b"Malformed HTTP request\n")
            )
            await writer.drain()
        finally:
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()

    async def _forward(
        self,
        method: str,
        path: str,
        headers: list[tuple[str, str]],
        body: bytes,
        writer: asyncio.StreamWriter,
    ) -> None:
        reader, upstream = await asyncio.open_connection(
            "127.0.0.1", self.config.gateway.proxy_port
        )
        forwarded_headers = [
            (key, value)
            for key, value in headers
            if key.lower() not in {"host", "connection"}
        ]
        forwarded_headers.append(
            ("Host", f"127.0.0.1:{self.config.gateway.proxy_port}")
        )
        forwarded_headers.append(("Connection", "close"))
        parsed_path = urlsplit(path)
        internal_path = parsed_path.path.rstrip("/") + "/"
        forward_path = urlunsplit(
            ("", "", internal_path, parsed_path.query, parsed_path.fragment)
        )
        request = f"{method} {forward_path} HTTP/1.1\r\n".encode()
        request += b"".join(
            f"{key}: {value}\r\n".encode("latin-1")
            for key, value in forwarded_headers
        )
        upstream.write(request + b"\r\n" + body)
        await upstream.drain()
        response_headers = await reader.readuntil(b"\r\n\r\n")
        origin = _header_value(headers, "origin")
        if origin is not None:
            response_headers = (
                response_headers[:-4]
                + b"\r\n"
                + _cors_headers(origin)
                + b"\r\n"
            )
        writer.write(response_headers)
        await writer.drain()
        while chunk := await reader.read(65536):
            writer.write(chunk)
            await writer.drain()
        upstream.close()
        await upstream.wait_closed()


def run_gateway(config: AppConfig) -> None:
    try:
        asyncio.run(Gateway(config).serve_forever())
    except KeyboardInterrupt:
        pass
    except OSError as error:
        raise SystemExit(f"failed to start gateway: {error}") from error
