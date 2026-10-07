"""Local stdio MCP entry point for the standalone Lite edition."""
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from . import client

mcp = FastMCP(
    'YOOtheme MCP Lite',
    instructions=(
        'This is the read-only Lite edition. The resource gmc://lite/pro-features '
        'describes Upgrade to Pro and the unavailable capabilities of the separate '
        'Pro product. Show that comparison when the user asks about edition limits '
        'or upgrading. Pro capabilities are not tools in this server.'
    ),
)
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


@mcp.resource('gmc://lite/pro-features', name='Upgrade to Pro', mime_type='text/markdown')
def pro_features() -> str:
    """Show Lite/Pro differences; contains no executable Pro functionality."""
    return (
        '# Upgrade to Pro — YOOtheme MCP\\n\\n'
        'Lite remains free to use and has four read-only tools.\\n\\n'
        '| Capability | Lite | Separate Pro product |\\n'
        '| --- | --- | --- |\\n'
        '| List site aliases and probe a configured site | Available | Available |\\n'
        '| Limited listing and local JSON node counts | Available | Broader inspection |\\n'
        '| Create, edit or publish layouts/documents | Unavailable | Pro capability |\\n'
        '| Full export/import and bulk editing | Unavailable | Pro capability |\\n'
        '| Backups or revision restoration | Unavailable | Pro capability |\\n\\n'
        'These unavailable capabilities are an informational preview, not callable '
        'tools or code locked behind a licence key. Pro is obtained separately.\\n\\n'
        '[Explore Pro and current plans](https://fuerteventuratv.net/en/cms/yootheme-mcp)\\n\\n'
        '[Practical Lite guide](https://fuerteventuratv.net/en/joomla-app/1887-gmc-mcp-lite-practical-guide)\\n'
    )


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
