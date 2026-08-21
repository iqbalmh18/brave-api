# Instalasi

## Persyaratan

- Python 3.11 atau lebih baru
- [`uv`](https://docs.astral.sh/uv/) atau `pip`

```bash
uv add brave-api-python
```

Untuk MCP server:

```bash
uv add "brave-api-python[mcp]"
```

Alternatif dengan pip:

```bash
pip install brave-api-python
pip install "brave-api-python[mcp]"
```

## Dari source

```bash
git clone https://github.com/iqbalmh18/brave-api.git
cd brave-api
uv sync --group dev
uv run python -c "from brave_api import BraveClient; print('installed')"
```

Akses Brave Search memerlukan koneksi internet.
