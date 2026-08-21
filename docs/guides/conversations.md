# Conversations

Use `conversation()` for multi-turn Ask sessions:

Each conversation has an `id` and `symmetric_key`. Keep both when sending a
follow-up as part of the same conversation.

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

Call `collect()` to combine all events into a final result. For an interactive
UI, iterate over `stream_events()` and handle each `StreamEventType`.
