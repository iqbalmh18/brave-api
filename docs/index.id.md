# brave-api-python

<img src="../brave-api.svg" alt="Banner animasi adaptif brave-api-python" />

Client Python asynchronous dan typed untuk Brave Search dan Brave Ask, dengan
MCP server bawaan.

## Fitur

- Jawaban AI lengkap atau streaming
- Percakapan multi-turn dan input gambar
- Search web, images, news, videos, dan Brave Goggles terstruktur
- Model Pydantic typed, retry, proxy, timeout, dan exception konsisten
- MCP melalui stdio atau HTTP

## Instalasi cepat

```bash
uv add brave-api-python
```

## Penggunaan minimal

```python
import asyncio
from brave_api import BraveClient

async def main() -> None:
    async with BraveClient() as client:
        answer = await client.ask("Apa itu komputasi kuantum?")
        print(answer.text)
        result = await client.search("tutorial Python asyncio")
        for item in result.web[:3]:
            print(item.title, item.url)

asyncio.run(main())
```

Semua operasi network bersifat async. Baca [Mulai Cepat](quickstart.id.md),
[Panduan Ask](guides/ask.id.md), [Panduan Search](guides/search.id.md), dan
[Referensi API](api.id.md) untuk penjelasan lengkap.
Lihat juga [Troubleshooting](guides/troubleshooting.id.md) untuk lifecycle,
error, retry, dan masalah koneksi.
