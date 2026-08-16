# Development

```bash
uv sync --group dev
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv build
```

Use Conventional Commit prefixes such as `feat:`, `fix:`, `docs:`, and
`test:`. See the repository `CONTRIBUTING.md` for release details.
