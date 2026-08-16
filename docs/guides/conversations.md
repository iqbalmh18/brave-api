# Conversations

Use `conversation()` for multi-turn Ask sessions:

```python
async with BraveClient() as client:
    conversation = await client.conversation("Explain DNS")
    first = await conversation.collect()

    followup = await client.conversation(
        "Now explain DNSSEC",
        conversation_id=conversation.id,
        symmetric_key=conversation.symmetric_key,
    )
    second = await followup.collect()
```

For incremental output, iterate over `conversation.stream_events()`.
