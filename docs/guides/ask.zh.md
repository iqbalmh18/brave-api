# Ask API

需要最终结果时使用 `ask()`，需要实时显示内容时使用 `ask_stream()`。

```python
async with BraveClient() as client:
    result = await client.ask("什么是 WebAssembly？")
print(result.text, result.urls, result.followups)
```

常用字段包括 `text`、`urls`、`images`、`videos` 和 `followups`，但每个
问题不一定都会返回所有字段。

## 流式响应

```python
from brave_api import BraveClient, StreamEventType
async with BraveClient() as client:
    async for event in client.ask_stream("什么是 WebAssembly？"):
        if event.type is StreamEventType.TEXT_DELTA:
            print(event.delta, end="", flush=True)
```

`image` 可以是 `pathlib.Path` 或受支持的 `ImageInput`。多轮问题请参阅
[对话](conversations.zh.md)。
