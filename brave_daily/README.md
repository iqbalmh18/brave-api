# Brave Daily

This is the automated daily intelligence dashboard deployed to GitHub Pages. It gathers real-time search, news, visual, and video intelligence using [`brave-api`](https://github.com/iqbalmh18/brave-api) across 6 specialized modules:

1. **🔍 Global Pulse**: Multi-domain daily briefings across Tech, Geopolitics, Finance, Cybersecurity, and Science.
2. **📊 Trend Radar**: Article volume momentum indicators across 10 key tech & society topics.
3. **🛡️ Threat Wire**: Cybersecurity and OSINT threat digest with automated severity scoring and indicator extraction.
4. **📡 Market Scanner**: Financial market signals and macro-economy sentiment summaries.
5. **📥 Data Lab**: Machine-readable data exports (Full JSON, CSV spreadsheet, STIX-lite threat feed JSON, and Markdown report).
6. **🌐 Search Playground**: Interactive API demonstration showcasing real code examples and live search responses.

## Local generation

```bash
uv run python brave_daily/generate.py --output brave_daily/dist
python -m http.server 8000 --directory brave_daily/dist
```

Open `http://127.0.0.1:8000` after generation. A live Brave connection or valid API setup is required for fresh generation.

## GitHub Pages

The scheduled GitHub Actions workflow runs daily at 01:15 UTC (`.github/workflows/brave-daily.yml`). It generates `intel.json`, `threats.json`, `export.csv`, and `report.md` alongside the static dashboard and deploys them via GitHub Pages Actions.
