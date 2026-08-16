# Ask API

## Blocking answer

`ask()` returns a complete `StreamResult` containing the answer, sources,
images, videos, infobox, and follow-up questions when available.

```python
async with BraveClient() as client:
    result = await client.ask("What is WebAssembly?")

print(result.text)
print(result.urls)
print(result.followups)
```

## Streaming

```python
from brave_api import BraveClient, StreamEventType

async with BraveClient() as client:
    async for event in client.ask_stream("What is WebAssembly?"):
        if event.type is StreamEventType.TEXT_DELTA:
            print(event.delta, end="", flush=True)
```

## Image input

```python
from pathlib import Path

async with BraveClient() as client:
    result = await client.ask(
        "What is shown in this image?",
        image=Path("photo.jpg"),
    )
```
