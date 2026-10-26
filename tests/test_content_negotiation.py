"""Exercise real HTTP requests at the Joomla/WordPress content-negotiation boundary."""
import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from yootheme_mcp_lite import client


class ContentNegotiationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.requests = []
        requests = self.requests

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                requests.append((self.path, self.headers.get("Accept")))
                joomla = self.path.startswith("/api/index.php/v1/")
                expected = "application/vnd.api+json" if joomla else "application/json"
                status = getattr(self.server, "forced_status", None) or (200 if self.headers.get("Accept") == expected else 406)
                payload = {"data": [{"id": "1", "attributes": {"title": "Article", "state": 1}}]} if joomla else [{"id": 1, "title": {"rendered": "Page"}, "status": "publish"}]
                body = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", expected)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.tmp = tempfile.TemporaryDirectory()
        config = Path(self.tmp.name) / "sites.json"
        base = "http://127.0.0.1:" + str(self.server.server_port)
        config.write_text(json.dumps({"sites": {
            "joomla": {"platform": "joomla", "url": base, "joomla_token_env": "TEST_JOOMLA_TOKEN"},
            "wordpress": {"platform": "wordpress", "url": base, "username_env": "TEST_WP_USER", "password_env": "TEST_WP_PASS"},
        }}), encoding="utf-8")
        self.env = patch.dict(os.environ, {client.CONFIG_ENV: str(config), "TEST_JOOMLA_TOKEN": "fixture-token", "TEST_WP_USER": "fixture-user", "TEST_WP_PASS": "fixture-password"})
        self.env.start()
        client._gates.clear()
        client._last_request.clear()
        client._blocked.clear()

    def tearDown(self):
        self.env.stop()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    async def test_joomla_article_listing_uses_json_api_accept(self):
        try:
            result = await client.list_items("joomla", 1)
        except client.LiteError as error:
            self.fail(str(error))
        self.assertEqual(result["items"][0]["title"], "Article")
        self.assertEqual(self.requests[0][1], "application/vnd.api+json")

    async def test_wordpress_page_listing_keeps_json_accept(self):
        result = await client.list_items("wordpress", 1)
        self.assertEqual(result["items"][0]["title"], "Page")
        self.assertEqual(self.requests[0][1], "application/json")

    async def test_forbidden_responses_stop_further_site_requests(self):
        for status in (403, 415):
            with self.subTest(status=status):
                self.server.forced_status = status
                client._blocked.clear()
                client._last_request.clear()
                before = len(self.requests)
                with self.assertRaisesRegex(client.LiteError, f"HTTP {status}"):
                    await client.list_items("joomla", 1)
                with self.assertRaisesRegex(client.LiteError, "requests stopped"):
                    await client.list_items("joomla", 1)
                self.assertEqual(len(self.requests), before + 1)

    async def test_unlisted_route_is_rejected_before_network_access(self):
        with self.assertRaisesRegex(client.LiteError, "allowlist"):
            await client._get("joomla", "users")
        self.assertEqual(self.requests, [])


if __name__ == "__main__":
    unittest.main()
