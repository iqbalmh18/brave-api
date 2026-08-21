# 开发

```bash
uv sync --group dev
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv build
```

本地构建文档：

```bash
uv sync --group docs
uv run mkdocs build --strict
```

提交信息请使用 Conventional Commit 前缀，例如 `feat:`、`fix:`、`docs:`
和 `test:`。
