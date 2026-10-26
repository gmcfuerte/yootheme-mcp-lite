"""Check the resource content delivered through the installed MCP SDK."""
import unittest

from yootheme_mcp_lite.__main__ import mcp


class ResourceTests(unittest.IsolatedAsyncioTestCase):
    async def test_upgrade_resource_contains_renderable_markdown(self):
        resources = list(await mcp.read_resource("gmc://lite/pro-features"))
        self.assertEqual(len(resources), 1)
        self.assertEqual(resources[0].mime_type, "text/markdown")
        text = resources[0].content
        self.assertNotIn(r"\n", text)
        self.assertIn("\n\n| Capability | Lite | Separate Pro product |\n", text)
        self.assertIn("\n| --- | --- | --- |\n", text)
