# MCP server

MCP server menghubungkan client Model Context Protocol dengan Brave Search.
Install extra-nya:

```bash
uv add "brave-api-python[mcp]"
brave-api-mcp
```

Mode HTTP:

```bash
brave-api-mcp --http --host 127.0.0.1 --port 8000
```

Tool tersedia: `ask`, `search`, `search_images`, `search_news`,
`search_videos`, `search_goggles`, dan `suggest`.

Konfigurasi environment yang umum: `BRAVE_BASE_URL`, `BRAVE_COUNTRY`,
`BRAVE_LANGUAGE`, `BRAVE_UI_LANG`, `BRAVE_SAFESEARCH`,
`BRAVE_REQUEST_TIMEOUT`, `BRAVE_MAX_RETRIES`, `BRAVE_MAX_CONCURRENT`, dan
`BRAVE_PROXY_LIST` (daftar URL dipisahkan koma).
