import pytest

from custom_mcp_servers import __doc__
from custom_mcp_servers.cli import SERVER_COMMANDS, build_parser, main


def test_package_imports() -> None:
    assert __doc__


def test_launcher_flags_select_a_server() -> None:
    arguments = build_parser().parse_args(["--duckduckgo-mcp-server"])

    assert arguments.server == "duckduckgo"
    assert SERVER_COMMANDS[arguments.server] == ("uvx", "duckduckgo-mcp-server")


def test_launcher_rejects_multiple_servers() -> None:
    parser = build_parser()

    try:
        parser.parse_args(["--time", "--fetch"])
    except SystemExit as error:
        assert error.code == 2
    else:
        raise AssertionError("Expected mutually exclusive server flags to fail")


def test_launcher_accepts_duckduckgo_http_options() -> None:
    arguments = build_parser().parse_args(
        ["--duckduckgo", "--host", "127.0.0.1", "--port", "8000"]
    )

    assert arguments.server == "duckduckgo"
    assert arguments.host == "127.0.0.1"
    assert arguments.port == 8000


def test_time_http_mode_uses_the_stdio_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launched: list[str] = []

    def fake_execvp(program: str, arguments: list[str]) -> None:
        assert program == "uvx"
        launched.extend(arguments)

    monkeypatch.setattr("custom_mcp_servers.cli.os.execvp", fake_execvp)

    main(["--time", "--host", "0.0.0.0", "--port", "8001"])

    assert launched == [
        "uvx",
        "--with",
        "mcp<2",
        "mcp-proxy",
        "--host",
        "0.0.0.0",
        "--port",
        "8001",
        "--",
        "uvx",
        "--with",
        "mcp<2",
        "mcp-server-time",
    ]
