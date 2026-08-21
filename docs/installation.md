# Installation

This guide installs the library for a new application. No extra configuration
is required to create a client; optional settings are covered in
[Configuration](guides/configuration.md).

## Requirements

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) (recommended) or `pip`

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

The last command installs development and documentation dependencies. Verify
the installation with:

```bash
uv run python -c "from brave_api import BraveClient; print('installed')"
```

This is an HTTP client; using Brave Search requires an internet connection and
may be affected by upstream service changes.
