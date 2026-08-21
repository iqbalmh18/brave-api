# API 参考

本页由 package 的 docstring 和签名自动生成。主要入口是 `BraveClient`；使用
`ClientConfig` 配置请求，使用类型模型读取结果，并根据异常层次处理错误。

## 主要客户端

- `BraveClient`：`open()`、`close()`、`health_check()`、`ask()`、
  `ask_stream()`、`conversation()`、`search()`、各 vertical 搜索方法和
  `suggest()`。
- `ClientConfig`：配置 URL、语言、地区、安全搜索、超时、重试、并发、请求
  header 和代理的不可变模型。
- `Conversation`：管理多轮会话，提供 `collect()` 和 `stream_events()`。

## 结果模型

`StreamResult`、`StreamEvent`、`ConversationResponse`、`SearchResult`、
`WebResult`、`NewsResult`、`ImageResult`、`VideoResult`、`Infobox`、
`SuggestResult` 和 `SuggestItem` 都是类型安全的 Pydantic 模型，可使用点号
访问字段或调用 `.model_dump()`。

## 枚举和异常

公共枚举包括 `QueryType`、`SearchType`、`StreamEventType` 和 `StreamState`。
所有异常都继承 `BraveAPIError`，常用子类包括 `HTTPStatusError`、
`TransportError`、`ResponseParseError`、`ConversationError`、
`ChallengeRequiredError`、`StreamAbortedError` 和 `TokenExtractionError`。

完整签名和 docstring 请参阅[英文 API 参考](api.md)。

完整 API 参考由 source code 中的类型注解和 docstring 自动生成。请访问
[English API Reference](https://brave-api.readthedocs.io/api/)，查看完整的
class、method、model、enum 和 exception 列表。

主要范围：

- 用于 Ask、对话和搜索 verticals 的 `BraveClient`。
- endpoint、token、timeout、retry、proxy 和 locale 配置。
- Web、image、news、video 和 Goggles response 的 Pydantic model。
- request、response、authentication 和 parsing 错误的 exception 层级。
