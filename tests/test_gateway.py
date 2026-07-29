import asyncio

import pytest

from custom_mcp_servers.config import AppConfig, GatewayConfig, ServerConfig
from custom_mcp_servers.gateway import Gateway


def config_for(port: int, proxy_port: int) -> AppConfig:
    return AppConfig(
        GatewayConfig(
            "127.0.0.1", port, proxy_port, ("test.local",), ("http://allowed",)
        ),
        (ServerConfig("stub", True, ("stub",)),),
    )


def run(coro):
    try:
        return asyncio.run(coro)
    except PermissionError:
        pytest.skip("network sockets are unavailable in this environment")


async def request(port: int, origin: str | None = "http://allowed") -> bytes:
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    extra = f"Origin: {origin}\r\n" if origin is not None else ""
    writer.write(
        f"POST /servers/stub/mcp HTTP/1.1\r\nHost: test.local\r\n"
        f"Content-Length: 2\r\n{extra}\r\nhi".encode()
    )
    await writer.drain()
    result = await reader.read()
    writer.close()
    await writer.wait_closed()
    return result


def test_gateway_rejects_unlisted_origin() -> None:
    async def scenario() -> bytes:
        gateway = Gateway(config_for(0, 0))
        gateway.server = await asyncio.start_server(
            gateway._handle, "127.0.0.1", 0
        )
        port = gateway.server.sockets[0].getsockname()[1]
        result = await request(port, "http://blocked")
        await gateway.close()
        return result

    assert run(scenario()).startswith(b"HTTP/1.1 403 Forbidden")


def test_gateway_forwards_valid_request_and_response_headers() -> None:
    async def scenario() -> bytes:
        async def upstream(reader, writer) -> None:
            await reader.readuntil(b"\r\n\r\n")
            await reader.readexactly(2)
            writer.write(
                b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n"
                b"Mcp-Session-Id: session-1\r\n\r\nok"
            )
            await writer.drain()
            writer.close()

        upstream_server = await asyncio.start_server(upstream, "127.0.0.1", 0)
        proxy_port = upstream_server.sockets[0].getsockname()[1]
        gateway = Gateway(config_for(0, proxy_port))
        gateway.server = await asyncio.start_server(
            gateway._handle, "127.0.0.1", 0
        )
        port = gateway.server.sockets[0].getsockname()[1]
        result = await request(port)
        await gateway.close()
        upstream_server.close()
        await upstream_server.wait_closed()
        return result

    result = run(scenario())
    assert result.startswith(b"HTTP/1.1 200 OK")
    assert b"Mcp-Session-Id: session-1" in result
    assert result.endswith(b"ok")
