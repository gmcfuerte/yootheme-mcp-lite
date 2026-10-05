"""Minimal read-only transport; no dependency on the paid implementation."""
import asyncio
import html
import ipaddress
import json
import os
import re
import time
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlsplit

import httpx

PRODUCT = 'yootheme'
CONFIG_ENV = 'YOOTHEME_MCP_LITE_SITES'
_gates: dict[str, asyncio.Lock] = {}
_last_request: dict[str, float] = {}
_blocked: set[str] = set()


class LiteError(ValueError):
    """Sanitized errors safe to return over MCP."""


def _config() -> dict:
    path = os.getenv(CONFIG_ENV)
    if not path:
        return {}
    try:
        file = Path(path)
        if file.stat().st_size > 65536:
            raise LiteError("Site configuration exceeds 64 KiB.")
        root = json.loads(file.read_text(encoding="utf-8"))
        sites = root["sites"]
        if not isinstance(sites, dict) or len(sites) > 50:
            raise LiteError("Expected a sites object with at most 50 entries.")
        for name, site in sites.items():
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", name) or not isinstance(site, dict):
                raise LiteError("Invalid site entry.")
            if site.get("platform") not in ("wordpress", "joomla"):
                raise LiteError("Platform must be wordpress or joomla.")
        return sites
    except (OSError, UnicodeError, KeyError, TypeError, RecursionError, json.JSONDecodeError):
        raise LiteError("Cannot read site configuration; check the local JSON file.") from None


def _site(name: str) -> dict:
    site = _config().get(name)
    if site is None:
        raise LiteError("Unknown site; configure it in the local sites JSON file.")
    if site.get("platform") not in ("wordpress", "joomla"):
        raise LiteError("Platform must be wordpress or joomla.")
    if PRODUCT == "elementor" and site["platform"] != "wordpress":
        raise LiteError("Elementor Lite supports WordPress only.")
    url = site.get("url", "")
    try:
        parts = urlsplit(url)
        host = parts.hostname
        parts.port
        try:
            loopback = ipaddress.ip_address(host or "").is_loopback
        except ValueError:
            loopback = host == "localhost"
        invalid_path = any(p in (".", "..") for p in unquote(parts.path).split("/"))
        if (not host or parts.username is not None or parts.password is not None
                or parts.query or parts.fragment or invalid_path
                or "\\" in url or re.search(r"[\x00-\x20]", url)
                or (parts.scheme != "https" and not (parts.scheme == "http" and loopback))):
            raise LiteError("Use HTTPS without URL credentials or queries; HTTP is loopback-only.")
    except (TypeError, ValueError):
        raise LiteError("Invalid site URL; use HTTPS or an exact HTTP loopback host.") from None
    if site.get("rest_mode", "pretty") not in ("pretty", "query"):
        raise LiteError("rest_mode must be pretty or query.")
    return site


def _secret(site: dict, field: str) -> str:
    name = site.get(field, "")
    if not isinstance(name, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{1,127}", name):
        raise LiteError("Configure credential environment-variable names in sites JSON.")
    value = os.getenv(name)
    if not value:
        raise LiteError("A required credential environment variable is unset.")
    return value


def _text(value) -> str:
    if not isinstance(value, str):
        return ""
    return html.unescape(re.sub(r"<[^>]*>", "", value))[:200]


def _label(value) -> str | None:
    if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.:/-]{1,64}", value):
        return value
    return None


async def _get(name: str, route: str, params: dict | None = None):
    site = _site(name)
    platform = site["platform"]
    allowed = ({"wp/v2/users/me", "wp/v2/pages"} if PRODUCT == "yootheme" else
               {"gmc-builder/v1/elements"} if PRODUCT == "gmcbuilder" else
               {"gmc-elementor-mcp/v1/ping", "gmc-elementor-mcp/v1/documents"})
    if platform == "joomla":
        allowed = ({"content/articles"} if PRODUCT == "yootheme" else {"list_elements"})
    if route not in allowed:
        raise LiteError("Endpoint is outside the Lite read allowlist.")
    headers = {"Accept": "application/json", "User-Agent": PRODUCT + "-mcp-lite/0.1.0"}
    auth = None
    query = dict(params or {})
    if platform == "wordpress":
        auth = httpx.BasicAuth(_secret(site, "username_env"), _secret(site, "password_env"))
        if site.get("rest_mode", "pretty") == "query":
            path = "/index.php"
            query["rest_route"] = "/" + route
        else:
            path = "/wp-json/" + route
    elif PRODUCT == "gmcbuilder":
        path = "/index.php"
        query.update(option="com_ajax", group="content", plugin="gmcbuilder",
                     format="json", action="list_elements")
        headers["X-Gmc-Builder-Key"] = _secret(site, "builder_key_env")
    else:
        path = "/api/index.php/v1/" + route
        headers["X-Joomla-Token"] = _secret(site, "joomla_token_env")
    base = site["url"].rstrip("/")
    # Aliases of the same endpoint share the throttle and fail-stop state.
    gate_key = base.lower()
    gate = _gates.setdefault(gate_key, asyncio.Lock())
    async with gate:
        if gate_key in _blocked:
            raise LiteError("Site requests stopped after HTTP 403/415; resolve access then restart.")
        delay = 2.0 - (time.monotonic() - _last_request.get(gate_key, 0.0))
        if delay > 0:
            await asyncio.sleep(delay)
        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=False, verify=True,
                                        trust_env=False) as client:
                async with client.stream("GET", base + path, params=query,
                                         headers=headers, auth=auth) as response:
                    status = response.status_code
                    if status in (403, 415):
                        _blocked.add(gate_key)
                    if status != 200:
                        raise LiteError(f"Read failed with HTTP {status}; no retry was attempted.")
                    chunks = []
                    size = 0
                    async for chunk in response.aiter_bytes():
                        size += len(chunk)
                        if size > 1048576:
                            raise LiteError("API response exceeds the Lite 1 MiB limit.")
                        chunks.append(chunk)
                    payload = json.loads(b"".join(chunks))
            return payload
        except (httpx.HTTPError, ValueError, UnicodeError) as error:
            if isinstance(error, LiteError):
                raise
            raise LiteError("Read failed; check connection, authentication and API availability.") from None
        finally:
            _last_request[gate_key] = time.monotonic()


def list_sites() -> dict:
    return {"sites": [{"name": name, "platform": site.get("platform", "")}
                       for name, site in sorted(_config().items())], "edition": "Lite"}


async def list_items(name: str, limit: int = 10) -> dict:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 10:
        raise LiteError("Lite limit must be an integer from 1 to 10.")
    site = _site(name)
    if PRODUCT == "gmcbuilder":
        route = "gmc-builder/v1/elements" if site["platform"] == "wordpress" else "list_elements"
        data = await _get(name, route)
        if not isinstance(data, dict):
            raise LiteError("Unexpected builder API response.")
        if data.get("success") is False or data.get("ok") is False:
            raise LiteError("Builder API rejected the read.")
        body = data.get("data", data)
        if not isinstance(body, dict) or body.get("ok") is False:
            raise LiteError("Unexpected builder API response.")
        schema = body.get("schema", body)
        elements = schema.get("elements", {}) if isinstance(schema, dict) else {}
        labels = elements.keys() if isinstance(elements, dict) else [
            item.get("type", item.get("name")) for item in elements if isinstance(item, dict)
        ] if isinstance(elements, list) else []
        names = sorted({label for item in labels if (label := _label(item))})
        return {"element_types": names[:limit], "available_count": len(names), "limit": limit}
    if PRODUCT == "elementor":
        data = await _get(name, "gmc-elementor-mcp/v1/documents",
                          {"per_page": limit, "offset": 0, "only_with_elementor": 1})
        rows = data.get("items") if isinstance(data, dict) else None
    elif site["platform"] == "wordpress":
        rows = await _get(name, "wp/v2/pages", {"per_page": limit, "context": "edit",
                          "_fields": "id,title,status"})
    else:
        data = await _get(name, "content/articles", {"page[limit]": limit,
                         "page[offset]": 0, "fields[articles]": "id,title,state"})
        rows = data.get("data") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise LiteError("Unexpected document API response.")
    items = []
    for row in rows[:limit]:
        if not isinstance(row, dict):
            continue
        attributes = row.get("attributes", row)
        if not isinstance(attributes, dict):
            continue
        title = attributes.get("title", "")
        if isinstance(title, dict):
            title = title.get("rendered", "")
        identifier = row.get("id")
        if not isinstance(identifier, (int, str)):
            continue
        items.append({"id": str(identifier)[:40], "title": _text(title),
                      "status": _text(str(attributes.get("status", attributes.get("state", ""))))})
    return {"items": items, "limit": limit, "edition": "Lite"}


async def ping_site(name: str) -> dict:
    site = _site(name)
    if PRODUCT == "elementor":
        data = await _get(name, "gmc-elementor-mcp/v1/ping")
        if not isinstance(data, dict) or data.get("ok") is False:
            raise LiteError("Unexpected companion API response.")
    elif PRODUCT == "yootheme" and site["platform"] == "wordpress":
        data = await _get(name, "wp/v2/users/me", {"_fields": "id"})
        if not isinstance(data, dict) or not isinstance(data.get("id"), int):
            raise LiteError("Authenticated user probe returned an unexpected response.")
    else:
        await list_items(name, 1)
    return {"site": name, "platform": site["platform"], "reachable": True, "edition": "Lite"}


def summarize_layout(layout_json: str) -> dict:
    """Count node types from supplied JSON without returning settings or content."""
    if len(layout_json.encode("utf-8")) > 65536:
        raise LiteError("Lite layout input exceeds 64 KiB.")
    try:
        root = json.loads(layout_json)
    except (ValueError, RecursionError):
        raise LiteError("Provide a JSON object or array containing layout nodes.") from None
    if not isinstance(root, (dict, list)):
        raise LiteError("Provide a JSON object or array containing layout nodes.")
    queue = [(root, 0)]
    counts = Counter()
    visited = 0
    while queue:
        node, depth = queue.pop()
        visited += 1
        if visited > 5000 or depth > 32:
            raise LiteError("Layout exceeds Lite traversal limits.")
        if isinstance(node, list):
            queue.extend((item, depth + 1) for item in node)
        elif isinstance(node, dict):
            kind = node.get("widgetType") or node.get("elType") or node.get("type")
            label = _label(kind)
            if label:
                counts[label] += 1
            for key in ("children", "elements", "layout", "rows", "columns", "sections"):
                child = node.get(key)
                if isinstance(child, (dict, list)):
                    queue.append((child, depth + 1))
    return {"node_count": sum(counts.values()), "node_types": dict(sorted(counts.items())),
            "edition": "Lite"}
