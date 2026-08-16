# Search API

## Vertical search

All search methods return the same `SearchResult` envelope:

```python
async with BraveClient() as client:
    web = await client.search("Python asyncio")
    images = await client.search_images("Python logo")
    news = await client.search_news("Python release")
    videos = await client.search_videos("Python tutorial")
    goggles = await client.search_goggles("privacy search")
```

| Method | Populated field |
|---|---|
| `search()` | `web`, `news` |
| `search_images()` | `images` |
| `search_news()` | `news` |
| `search_videos()` | `videos` |
| `search_goggles()` | `web` |

## Pagination

Brave uses `offset` as a page number. The first page is `0`:

```python
page1 = await client.search_news("Python release", offset=0)
page2 = await client.search_news("Python release", offset=1)
print(page2.offset, page2.has_more)
```

Use `spellcheck=False` for exact keyword matching.

## Autocomplete

```python
suggestions = await client.suggest("pyth")
for item in suggestions.suggestions:
    print(item.text, item.entity_type)
```
