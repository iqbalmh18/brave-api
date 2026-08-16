# Configuration

```python
from brave_api import BraveClient, ClientConfig

config = ClientConfig(
    language="id",
    ui_lang="id-id",
    country="id",
    safesearch="moderate",
    timeout=60.0,
    max_retries=3,
)

async with BraveClient(config) as client:
    result = await client.search("berita teknologi")
```

Important options include `base_url`, `language`, `ui_lang`, `country`,
`geoloc`, `safesearch`, `timeout`, `stream_timeout`, `max_retries`,
`max_concurrent`, `extra_headers`, and `proxies`.

## Proxies

```python
config = ClientConfig(
    proxies=[
        "http://user:password@proxy-1.example:8080",
        "socks5://proxy-2.example:1080",
    ]
)
```

`BRAVE_PROXY_LIST` is also supported by the MCP server as a comma-separated
list of proxy URLs.
