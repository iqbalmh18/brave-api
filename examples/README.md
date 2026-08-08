# Examples

Each example is self-contained and calls the live Brave API, so they require
network access and can take from seconds to a couple of minutes depending on
the length of the generated answer.

Run any example with:

```bash
uv run python examples/quickstart.py
```

| File | Demonstrates |
|---|---|
| `quickstart.py` | Minimal ask and result inspection |
| `streaming.py` | Real-time event streaming (text, thinking, tools) |
| `search_suggest.py` | Web search with pagination + autocomplete |
| `multi_turn.py` | Resume, follow-up, and regenerate answers |
| `rich_results.py` | Images, videos, infobox, and follow-ups |
| `multimodal.py` | Vision mode: attach an image to a query |
| `configuration.py` | Config: language, safety, timeouts, proxies |
| `errors.py` | The full exception hierarchy |
| `lifecycle.py` | Manual `open()` / `close()` lifecycle |
| `concurrency.py` | Parallel queries with one shared client |
| `mcp_server.py` | The built-in MCP server |
| `chat_repl.py` | Interactive terminal chat |

Set the optional `BRAVE_PROXY_LIST` environment variable (comma-separated
proxy URLs) to exercise proxy rotation in `configuration.py`:

```bash
BRAVE_PROXY_LIST="http://user:pass@proxy-1:8080,socks5://proxy-2:1080" \
    uv run python examples/configuration.py
```
