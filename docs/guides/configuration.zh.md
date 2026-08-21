# 配置

`ClientConfig` 在创建时验证字段，并且创建后不可修改。需要变更时请创建
新的配置对象。

```python
from brave_api import BraveClient, ClientConfig
config = ClientConfig(
    language="id", ui_lang="id-id", country="id",
    safesearch="moderate", timeout=60.0, max_retries=3,
)
async with BraveClient(config) as client:
    result = await client.search("technology news")
```

常用选项包括 `base_url`、`language`、`ui_lang`、`country`、`geoloc`、
`safesearch`、`timeout`、`stream_timeout`、`max_retries`、`max_concurrent`、
`extra_headers` 和 `proxies`。`language` 控制响应语言，`ui_lang` 控制界面语言。

```python
config = ClientConfig(proxies=["http://proxy.example:8080", "socks5://proxy.example:1080"])
```
