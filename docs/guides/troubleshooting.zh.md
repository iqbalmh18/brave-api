# 故障排查与可靠性

## 检查连接

`health_check()` 执行轻量连接检查，失败时返回 `False`：

```python
async with BraveClient() as client:
    if not await client.health_check():
        raise RuntimeError("Brave Search 不可访问")
```

这只能证明 base URL 有响应，不能保证具体的 Ask 或 Search 请求一定成功。

## 生命周期

推荐使用 `async with BraveClient()`。如果应用自己管理生命周期，请调用一次
`open()`，在关闭时调用 `close()`。不要在循环中为每个项目创建 client；复用
一个 client 才能正确使用 HTTP session、重试、并发限制和代理池。

## 异常和重试

符合条件的临时错误会在 `max_retries` 次内以指数退避重试。常见异常包括
`HTTPStatusError`、`TransportError`、`ResponseParseError` 和根异常
`BraveAPIError`。

`ChallengeRequiredError` 表示上游要求浏览器 challenge；
`ConversationError` 和 `StreamAbortedError` 表示对话或流被中断。生产日志中
不要记录 cookie、代理密码或完整原始事件数据。

## 常见问题

| 现象 | 检查项 |
|---|---|
| `ModuleNotFoundError` | 确认安装环境与 `uv run` 使用的环境相同。 |
| 超时 | 调大 `timeout`/`stream_timeout`，检查网络和代理。 |
| HTTP 403 或 challenge | 检查上游服务；单纯重试可能无效。 |
| 结果为空 | 检查使用了正确的 vertical 字段和 `has_results`。 |
| MCP 工具错误 | 使用 `--log-level info` 并检查环境变量。 |

本地测试使用 fake transport 和 fixture，不依赖在线服务。测试通过不代表
上游响应格式、限流或 challenge policy 永远不变。
