# Pengembangan

```bash
uv sync --group dev
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv build
```

Validasi docs dengan:

```bash
uv sync --group docs
uv run mkdocs build --strict
```

Gunakan Conventional Commit seperti `feat:`, `fix:`, `docs:`, dan `test:`.
