from pathlib import Path

import pytest

from custom_mcp_servers.config import load_config
from custom_mcp_servers.gateway import proxy_command
from custom_mcp_servers.servers import discover


def write_config(path: Path, servers: str) -> None:
    path.write_text(
        """[gateway]
bind_host = "192.168.1.20"
port = 8000
proxy_port = 18000
allowed_hosts = ["192.168.1.20:8000"]
allowed_origins = ["http://192.168.1.10:3000"]

"""
        + servers
    )


def test_config_loads_enabled_and_disabled_servers(tmp_path: Path) -> None:
    path = tmp_path / "servers.toml"
    write_config(
        path,
        '[[servers]]\nname = "one"\nenabled = true\ncommand = '
        '["stub", "one"]\n'
        '[[servers]]\nname = "two"\nenabled = false\ncommand = '
        '["stub", "two"]\n',
    )
    config = load_config(path)

    assert config.servers[0].endpoint_path == "/servers/one/mcp"
    assert config.endpoint_url(config.servers[0]) == (
        "http://192.168.1.20:8000/servers/one/mcp"
    )
    command = proxy_command(config)
    assert "127.0.0.1" in command
    assert "one" in command
    assert "two" not in command
    assert any("mcp<2" == item for item in command)


def test_config_rejects_duplicate_names(tmp_path: Path) -> None:
    path = tmp_path / "servers.toml"
    write_config(
        path,
        '[[servers]]\nname = "same"\ncommand = ["stub"]\n'
        '[[servers]]\nname = "same"\ncommand = ["stub"]\n',
    )
    with pytest.raises(ValueError, match="duplicate server name"):
        load_config(path)


def test_config_rejects_missing_path(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="not found"):
        load_config(tmp_path / "missing.toml")


def test_builtin_server_definitions_are_discovered() -> None:
    specs = discover()

    assert {spec.name for spec in specs} == {"duckduckgo", "fetch", "time"}
    assert all(spec.command for spec in specs)
