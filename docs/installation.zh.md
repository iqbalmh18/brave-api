# 安装

## 要求

- Python 3.11 或更高版本
- [`uv`](https://docs.astral.sh/uv/) 或 `pip`

```bash
uv add brave-api-python
uv add "brave-api-python[mcp]"  # 需要 MCP 时
```

也可以使用：

```bash
pip install brave-api-python
pip install "brave-api-python[mcp]"
```

## 从源码安装

```bash
git clone https://github.com/iqbalmh18/brave-api.git
cd brave-api
uv sync --group dev
uv run python -c "from brave_api import BraveClient; print('installed')"
```

访问 Brave Search 需要网络连接。
