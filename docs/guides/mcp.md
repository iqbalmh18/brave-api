# MCP server

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
