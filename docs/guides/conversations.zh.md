# 对话

使用 `conversation()` 创建多轮 Ask 会话。保存 `id` 和 `symmetric_key`，
以便发送后续问题。

```python
async with BraveClient() as client:
    conversation = await client.conversation("请解释 DNS")
    first = await conversation.collect()
    followup = await client.conversation(
        "现在解释 DNSSEC",
        conversation_id=conversation.id,
        symmetric_key=conversation.symmetric_key,
    )
    second = await followup.collect()
```

需要增量输出时，请遍历 `stream_events()`。
