# MCP server

The MCP server connects Model Context Protocol clients to Brave Search. It
shares one `BraveClient` for the server lifetime and exposes read-only tools.

Install the extra:

```bash
uv add "brave-api-python[mcp]"
```

Run stdio mode:

```bash
brave-api-mcp
```

Run HTTP mode:

```bash
brave-api-mcp --http --host 127.0.0.1 --port 8000
```

Available tools are `ask`, `search`, `search_images`, `search_news`,
`search_videos`, `search_goggles`, and `suggest`.

Common environment variables include `BRAVE_BASE_URL`, `BRAVE_COUNTRY`,
`BRAVE_LANGUAGE`, `BRAVE_UI_LANG`, `BRAVE_SAFESEARCH`,
`BRAVE_REQUEST_TIMEOUT`, `BRAVE_MAX_RETRIES`, `BRAVE_MAX_CONCURRENT`, and
`BRAVE_PROXY_LIST`.

The server also reads `BRAVE_GEOLOC`, `BRAVE_STREAM_TIMEOUT`, and
`BRAVE_ENABLE_RESEARCH`. Numeric values are parsed at startup; invalid numeric
or boolean values fall back to defaults with a warning. `BRAVE_SAFESEARCH` must
be `off`, `moderate`, or `strict`.

Stdio suits local clients that launch the server as a subprocess. HTTP is useful
when client and server run separately:

```bash
brave-api-mcp --http --host 127.0.0.1 --port 8000 --log-level info
```

Available tools are `ask`, `search`, `search_images`, `search_news`,
`search_videos`, `search_goggles`, and `suggest`. Library errors are translated
to `ToolError` for MCP clients.
