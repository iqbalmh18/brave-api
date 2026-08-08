"""Canonical package version.

This is the single source of truth for the version. `pyproject.toml` reads it
via `[tool.hatch.version] path = "brave_api/_version.py"`, so the installed
distribution metadata and the runtime value always agree.
"""

__version__ = "1.0.0"
