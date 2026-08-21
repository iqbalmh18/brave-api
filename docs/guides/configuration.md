# Configuration

`ClientConfig` validates values at construction and is frozen. Create a new
configuration to change settings; do not mutate it after the client starts.

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

`language` is the response language (for example `id`), while `ui_lang` is the
interface language (for example `id-id`). `timeout` applies to normal requests;
`stream_timeout=None` means streaming has no time limit.

### Defaults

| Option | Default | Meaning |
|---|---:|---|
| `base_url` | `https://search.brave.com` | Brave service base URL |
| `country` | `us` | ISO alpha-2 country code |
| `language` | `en` | Response language |
| `ui_lang` | `en-us` | Interface language |
| `safesearch` | `moderate` | Safe-search level |
| `timeout` | `120.0` | Non-streaming timeout in seconds |
| `max_retries` | `3` | Maximum retries for eligible failures |
| `max_concurrent` | `5` | Concurrent HTTP request limit |

Values are validated: country must be lowercase two-letter code, language must
be a BCP-47-like code, geolocation uses `latitude x longitude`, and proxies
must include a supported URL scheme.

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

Duplicate proxies are removed and proxies are used in rotation. If all proxies
fail, the transport can try a direct connection.
