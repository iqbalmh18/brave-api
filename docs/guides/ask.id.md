# API Ask

Gunakan `ask()` untuk hasil final dan `ask_stream()` untuk menampilkan jawaban
ketika event diterima.

```python
async with BraveClient() as client:
    result = await client.ask("Apa itu WebAssembly?")
print(result.text, result.urls, result.followups)
```

Field umum adalah `text`, `urls`, `images`, `videos`, dan `followups`; tidak
semua pertanyaan mengisi semua field.

## Streaming

```python
from brave_api import BraveClient, StreamEventType

async with BraveClient() as client:
    async for event in client.ask_stream("Apa itu WebAssembly?"):
        if event.type is StreamEventType.TEXT_DELTA:
            print(event.delta, end="", flush=True)
```

## Input gambar

`image` dapat berupa `pathlib.Path` atau `ImageInput` yang didukung. Untuk
pertanyaan lanjutan, lihat [Percakapan](conversations.id.md).
