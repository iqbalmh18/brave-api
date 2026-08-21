# Percakapan

Gunakan `conversation()` untuk pertanyaan multi-turn. Simpan `id` dan
`symmetric_key` untuk pertanyaan lanjutan.

```python
async with BraveClient() as client:
    conversation = await client.conversation("Jelaskan DNS")
    first = await conversation.collect()
    followup = await client.conversation(
        "Sekarang jelaskan DNSSEC",
        conversation_id=conversation.id,
        symmetric_key=conversation.symmetric_key,
    )
    second = await followup.collect()
```

Gunakan `stream_events()` jika ingin menerima output secara bertahap.
