"""A minimal MCP server that adds two numbers."""

from mcp.server.fastmcp import FastMCP  # ty: ignore[unresolved-import]

mcp = FastMCP("adder")


@mcp.tool()
def add(a: float, b: float) -> float:
    """Return the sum of two numbers."""
    return a + b


if __name__ == "__main__":
    mcp.run()
