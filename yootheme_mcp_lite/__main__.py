"""Local stdio MCP entry point for the standalone Lite edition."""
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from . import client

mcp = FastMCP('YOOtheme MCP Lite')
READ = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True,
                       openWorldHint=True)
LOCAL = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True,
                        openWorldHint=False)


@mcp.tool(name='yootheme_lite' + "_list_sites", annotations=LOCAL)
def list_sites() -> dict:
    """List configured site aliases and platform names; never expose credentials."""
    return client.list_sites()


@mcp.tool(name='yootheme_lite' + "_ping_site", annotations=READ)
async def ping_site(site: str) -> dict:
    """Perform a single authenticated read; return only connection status."""
    return await client.ping_site(site)


@mcp.tool(name='yootheme_lite_list_pages', annotations=READ)
async def list_items(site: str, limit: int = 10) -> dict:
    'List at most ten page/article titles, ids and status; no content export.'
    return await client.list_items(site, limit)


@mcp.tool(name='yootheme_lite' + "_summarize_layout", annotations=LOCAL)
def summarize_layout(layout_json: str) -> dict:
    """Summarize supplied JSON node types; never return layout content or settings."""
    return client.summarize_layout(layout_json)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
