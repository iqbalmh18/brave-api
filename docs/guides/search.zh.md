# Search API

Search 返回结构化 SERP 数据，而不是 AI 答案。所有方法都返回相同的
`SearchResult` 外层结构。

| 方法 | 填充字段 |
|---|---|
| `search()` | `web`、`news` |
| `search_images()` | `images` |
| `search_news()` | `news` |
| `search_videos()` | `videos` |
| `search_goggles()` | `web` |

## 分页

`offset` 是页码：`0` 表示第一页，`1` 表示第二页。`spellcheck=False` 可
用于精确关键词匹配。

```python
page = await client.search_news("Python release", offset=1)
print(page.offset, page.has_more)
```

## 自动补全

```python
suggestions = await client.suggest("pyth")
for item in suggestions.suggestions:
    print(item.text, item.entity_type)
```
