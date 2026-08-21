# 快速开始

客户端方法都是异步的，请使用 `async def`、`await` 和 `asyncio.run`。

## Ask

```python
import asyncio
from brave_api import BraveClient

async def main() -> None:
    async with BraveClient() as client:
        result = await client.ask("请解释 DNSSEC")
    print(result.text)

asyncio.run(main())
```

## Search

```python
async with BraveClient() as client:
    result = await client.search("Python asyncio tutorial")
for item in result.web[:5]:
    print(item.title, item.url)
```

`ask()` 返回 `StreamResult`，`search()` 返回 `SearchResult`；两者都是
Pydantic 模型，可以使用点号访问字段或调用 `.model_dump()`。
