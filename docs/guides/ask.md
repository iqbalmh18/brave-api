# Ask API

Ask sends a question to Brave AI. Use `ask()` when the application needs the
final result, or `ask_stream()` when the UI should display text as it arrives.

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

Common fields are `text`, `urls`, `images`, `videos`, and `followups`. A query
does not necessarily produce every field.

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

`image` can be a `Path` or another supported `ImageInput`. For follow-up
questions, see [Conversations](conversations.md).
