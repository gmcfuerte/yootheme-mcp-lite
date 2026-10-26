# YOOtheme MCP Lite

Free limited companion to the GMC Pro product. This is a separate **0.1.3**
client with a fresh history and only four read-only MCP tools. The Pro
implementation is absent from this repository.

[![Listed on mcpservers.org](https://mcpservers.org/badge.svg)](https://mcpservers.org/servers/gmcfuerte/yootheme-mcp-lite)

[![Listed on AllMCPs](https://allmcps.com/api/badge/gmc-yootheme-mcp-lite)](https://allmcps.com/mcp/gmc-yootheme-mcp-lite?verify=8e394cba-4695-474c-8797-17f853d501bc)


## Lite and Pro

| Capability | Lite | Pro product |
| --- | --- | --- |
| Configured site aliases | Yes | Yes |
| Authenticated connection probe | Yes | Yes |
| Up to 10 pages per call | Yes | Extended tools |
| Local supplied JSON: node counts/types | Yes, input up to 64 KiB | Detailed inspection |
| Create/edit/publish layouts or documents | No | Paid functionality |
| Full export/import, bulk editing, backups | No | Paid functionality |
| Private Pro implementation or CMS companion source | Absent | Separately distributed |

YOOtheme MCP Base costs **EUR 49/year** for three sites (12 months, manual renewal). See [current plans](https://fuerteventuratv.net/en/cms/yootheme-mcp).

Lite is free to use under the [limited commercial licence](LICENSE).
Source visibility does not grant redistribution or resale rights.

## Upgrade to Pro in your MCP client

Open the resource **Upgrade to Pro** (`gmc://lite/pro-features`) to see the
capability comparison and the product's current plans. Editing, publishing,
full import/export, bulk editing and restoration are labelled **unavailable
in Lite**. They are informational previews; no Pro code or executable Pro
tools are bundled. The free tools keep working without an upgrade.

MCP clients decide how resources are displayed, so this is not a guaranteed
popup or a graphical settings panel. Ask your assistant to read the resource
if its client does not expose a resource browser.

## Guide and presentation

- [Practical Lite guide (English)](https://fuerteventuratv.net/en/joomla-app/1887-gmc-mcp-lite-practical-guide): prerequisites, setup and a first read-only session.
- [Presentation for clients (Italian PDF)](https://fuerteventuratv.net/images/manuali-cms/GMC-MCP-presentazione-clienti-IT-20261012.pdf): a short overview of the three Lite clients and the separate Pro editions.
- [Pro features and annual plans](https://fuerteventuratv.net/en/cms/yootheme-mcp).

## Prerequisites

Python 3.10 or newer. WordPress REST API with an Application Password, or Joomla Web Services with a token. YOOtheme remains a separately licensed product. The generic page list does not prove YOOtheme is installed; layout counts operate on JSON you supply.

## Install from GitHub

```console
git clone https://github.com/gmcfuerte/yootheme-mcp-lite.git
cd yootheme-mcp-lite
python -m venv .venv
```

Windows:

```console
.venv\Scripts\python.exe -m pip install .
```

macOS/Linux:

```console
.venv/bin/python -m pip install .
```

This Lite edition is distributed through this GitHub repository; it has
not been published to PyPI. Do not install the separate full Pro package
as a substitute for Lite.

## Configure

1. Copy `sites.example.json` to a **local** `sites.json` and keep only the
   sites you own or are authorized to access. The file is ignored by Git.
2. Set the credential environment variables named by `username_env`,
   `password_env`, and the applicable Joomla token/key field. Never put
   credential values in committed JSON or an MCP chat.
3. Set `YOOTHEME_MCP_LITE_SITES` to the absolute path of that local JSON file.
4. Add the server using `mcp.example.json`: replace the placeholders with
   the absolute Python executable and configuration file paths. Ensure
   the MCP client passes the credential variables to its child process.
5. Start with `yootheme_lite_list_sites`, then `yootheme_lite_ping_site`.

`rest_mode: "query"` supports WordPress without pretty REST URLs; otherwise
use `pretty`. Subdirectory installations are supported in the base URL.

## Tools

- `yootheme_lite_list_sites`: aliases and platforms only.
- `yootheme_lite_ping_site`: one authenticated GET, sanitized status only.
- `yootheme_lite_list_pages`: List at most ten page/article titles, ids and status; no content export.
- `yootheme_lite_summarize_layout`: pass the text from `layout.example.json`
  as `layout_json`. Returns counts and types; no settings or content.

The server runs locally using **stdio**. No remote HTTP server, uploads,
arbitrary URLs, SSH, license switch or Pro modules are included. Online
tools use a fixed GET allowlist, verified TLS, no redirects, at most one
request at a time per configured base URL, a two-second interval, and a
1 MiB response limit. HTTP is accepted only for exact loopback hosts.
HTTP 403/415 stops subsequent requests to that base URL until restart.

## Release status

Version 0.1.3 fixes Joomla Web Services content negotiation: Joomla requests
use `Accept: application/vnd.api+json`, while WordPress keeps `application/json`.
Four HTTP regression tests cover both platforms, the endpoint allowlist and
the HTTP 403/415 fail-stop. On 26 October 2026, a clean Python 3.13 installation
with MCP SDK 1.30.0 passed stdio startup, all four tools and read-only calls
against disposable WordPress 7.1.3 and Joomla 6.1.4 sites with YOOtheme Pro
5.0.53. Package installation and upgrade from 0.1.2 were also checked.
These are scoped Windows laboratory results, not production, graphical-host
or cross-platform certification. YOOtheme remains separately licensed.

## Contact

[GMC](https://fuerteventuratv.net/en/cms) · gmcfuerte@gmail.com.
Independent GMC software; product names belong to their respective owners.
