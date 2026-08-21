# Development

Clone the repository, prepare an environment with `uv`, and run these checks
before committing:

```bash
uv sync --group dev
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv build
```

To check the documentation locally:

```bash
uv sync --group docs
uv run mkdocs build --strict
```

Translation files use locale suffixes: `page.md` for English, `page.id.md` for
Bahasa Indonesia, and `page.zh.md` for Chinese.

Use Conventional Commit prefixes such as `feat:`, `fix:`, `docs:`, and
`test:`. See the repository `CONTRIBUTING.md` for release details.
