# Mulai Cepat

Method client bersifat async, jadi gunakan `async def`, `await`, dan
`asyncio.run`.

## Ask

```python
import asyncio
from brave_api import BraveClient

async def main() -> None:
    async with BraveClient() as client:
        result = await client.ask("Jelaskan DNSSEC")
    print(result.text)

asyncio.run(main())
```

## Search

```python
async with BraveClient() as client:
    result = await client.search("tutorial Python asyncio")
for item in result.web[:5]:
    print(item.title, item.url)
```

`ask()` menghasilkan `StreamResult`, sedangkan `search()` menghasilkan
`SearchResult`. Keduanya mendukung akses field dengan dot notation dan
`.model_dump()`.
