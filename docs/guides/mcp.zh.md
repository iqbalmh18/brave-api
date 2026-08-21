# MCP 服务器

MCP 服务器把支持 Model Context Protocol 的客户端连接到 Brave Search。

```bash
uv add "brave-api-python[mcp]"
brave-api-mcp
brave-api-mcp --http --host 127.0.0.1 --port 8000
```

可用工具：`ask`、`search`、`search_images`、`search_news`、`search_videos`、
`search_goggles` 和 `suggest`。常用环境变量包括 `BRAVE_BASE_URL`、
`BRAVE_COUNTRY`、`BRAVE_LANGUAGE`、`BRAVE_UI_LANG`、`BRAVE_SAFESEARCH`、
`BRAVE_REQUEST_TIMEOUT`、`BRAVE_MAX_RETRIES`、`BRAVE_MAX_CONCURRENT` 和
`BRAVE_PROXY_LIST`（逗号分隔的代理 URL）。
