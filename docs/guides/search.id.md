# API Search

Search mengembalikan data SERP terstruktur, bukan jawaban AI. Semua method
menghasilkan envelope `SearchResult` yang sama.

| Method | Field terisi |
|---|---|
| `search()` | `web`, `news` |
| `search_images()` | `images` |
| `search_news()` | `news` |
| `search_videos()` | `videos` |
| `search_goggles()` | `web` |

## Pagination

`offset` adalah nomor halaman: `0` halaman pertama dan `1` halaman kedua.

```python
page = await client.search_news("rilis Python", offset=1)
print(page.offset, page.has_more)
```

Gunakan `spellcheck=False` untuk pencocokan kata yang persis.

## Autocomplete

```python
suggestions = await client.suggest("pyth")
for item in suggestions.suggestions:
    print(item.text, item.entity_type)
```
