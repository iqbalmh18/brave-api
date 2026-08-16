"""MkDocs build hooks."""

from pathlib import Path
from shutil import copyfile


def on_post_build(config: object) -> None:
    """Make the root sitemap available below every generated page URL.

    Material's alternate-language integration requests ``sitemap.xml`` relative
    to each alternate page. MkDocs emits one sitemap at the site root, so copy
    it into generated page directories after the build. The aliases are build
    artifacts and never become source documentation files.
    """

    site_dir = Path(config.site_dir)  # type: ignore[attr-defined]
    sitemap = site_dir / "sitemap.xml"
    if not sitemap.is_file():
        return

    for index in site_dir.rglob("index.html"):
        alias = index.parent / "sitemap.xml"
        if alias != sitemap:
            copyfile(sitemap, alias)
