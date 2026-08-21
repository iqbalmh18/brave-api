# Konfigurasi

`ClientConfig` memvalidasi nilai saat dibuat dan bersifat frozen. Buat object
baru jika ingin mengubah konfigurasi.

```python
from brave_api import BraveClient, ClientConfig

config = ClientConfig(
    language="id", ui_lang="id-id", country="id",
    safesearch="moderate", timeout=60.0, max_retries=3,
)
async with BraveClient(config) as client:
    result = await client.search("berita teknologi")
```

Opsi penting: `base_url`, `language`, `ui_lang`, `country`, `geoloc`,
`safesearch`, `timeout`, `stream_timeout`, `max_retries`, `max_concurrent`,
`extra_headers`, dan `proxies`. `language` mengatur bahasa respons, sedangkan
`ui_lang` mengatur bahasa antarmuka.

## Proxy

```python
config = ClientConfig(proxies=[
    "http://user:password@proxy.example:8080",
    "socks5://proxy.example:1080",
])
```

Proxy dipakai bergiliran; proxy duplikat dihapus.
