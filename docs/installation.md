# Installation

## Requirements

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/)

```bash
uv add brave-api-python
```

For the MCP server:

```bash
uv add "brave-api-python[mcp]"
```

Install with pip if needed:

```bash
pip install brave-api-python
pip install "brave-api-python[mcp]"
```

## From source

```bash
git clone https://github.com/iqbalmh18/brave-api.git
cd brave-api
uv sync --group dev
```
