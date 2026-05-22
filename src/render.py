"""Headless-Chromium screenshotter.

Given a directory containing index.html (and styles/assets), render each .html
page at a fixed viewport and save full-page PNG screenshots to an output dir.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from playwright.sync_api import sync_playwright

VIEWPORT = {"width": 1280, "height": 800}


def list_html_pages(site_dir: Path) -> List[Path]:
    return sorted(p for p in site_dir.glob("*.html"))


def render_site(site_dir: Path, out_dir: Path) -> List[Path]:
    """Render every .html in site_dir and write <name>.png into out_dir.

    Returns the list of generated PNG paths (sorted). Always uses the same
    viewport so screenshots are directly comparable.
    """
    site_dir = site_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    html_pages = list_html_pages(site_dir)
    if not html_pages:
        raise FileNotFoundError(f"No .html files in {site_dir}")

    pngs: List[Path] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            context = browser.new_context(viewport=VIEWPORT, device_scale_factor=1)
            page = context.new_page()
            for html in html_pages:
                page.goto(html.as_uri(), wait_until="networkidle")
                page.wait_for_timeout(200)
                out_png = out_dir / (html.stem + ".png")
                page.screenshot(path=str(out_png), full_page=True)
                pngs.append(out_png)
        finally:
            browser.close()
    return sorted(pngs)
