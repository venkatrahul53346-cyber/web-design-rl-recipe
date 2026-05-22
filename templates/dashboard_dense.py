"""A4 dashboard × dense × dark-native × data-viz-decor.

High-signal hard slot. Sidebar + topbar + dense data tables on dark.
Linear inbox, vercel dashboard.
"""
from __future__ import annotations

from src.spec import BrandSpec, StyleSpec, WebsiteSpec
from templates import _brands, _fonts, _palettes
from templates._base import (
    TemplateMeta, format_notes, make_rng, sample_brand, sample_sitemap,
)


META = TemplateMeta(
    name="dashboard_dense",
    archetype="A4",
    difficulty="hard",
    style_axes={
        "density":         "dense",
        "color_regime":    "dark-native",
        "typography":      "geometric-sans",
        "border_language": "hairline-1px",
        "motif":           "data-viz-decor",
    },
    brand_verticals=["saas", "devtools", "fintech"],
    palette_pool=_palettes.DARK_NATIVE,
    font_pool=_fonts.GEOMETRIC_SANS,
    font_pair_locked=None,
    sitemap_pool=["overview", "detail-view", "settings", "billing", "team", "login"],
    sitemap_min=6,
    sitemap_max=6,
    style_references=["linear.app", "vercel.com/dashboard", "planetscale.com"],
)

DESIGN_NOTES = (
    "Design reference: {references_csv}. Background near-black (#0A0A0B), "
    "panel surface slightly lighter (#15151A), text on dark (#E5E5E7 "
    "primary, #8A8A92 muted). Persistent left sidebar (~220px) with nav "
    "groups + collapsible sections. Persistent top bar with breadcrumbs "
    "+ search + user menu. Hairline 1px borders (#26262C) separate "
    "everything; no shadows.\n\n"
    "Overview page: KPI cards in a 4-column grid (number large, label "
    "small, sparkline beneath), then a wide chart (line or bar, faint "
    "grid lines), then a recent-activity feed and a data table below. "
    "Detail-view: header with breadcrumbs, filter row, dense data table "
    "with sortable columns and zebra-stripe-free hairline rows. Settings: "
    "left rail of categories, right pane with the active form. Billing: "
    "current plan card, invoice table with status pills, payment-method "
    "tile. Team: members table with role/status columns and an invite "
    "form.\n\n"
    "Numerals must use tabular figures (font-feature-settings 'tnum'). "
    "Charts can be SVG or simulated with divs + 1px borders; do not use "
    "library-specific markup. {brand_name}'s name appears as the logo "
    "lockup top-left of the sidebar.\n\n"
    "Avoid: rounded cards larger than 8px radius, oversized hero "
    "treatments (this is an app shell, not a landing page), gradient "
    "decorations on data charts."
)


def sample_spec(seed: int) -> WebsiteSpec:
    rng = make_rng(seed)
    brand = sample_brand(rng, _brands.BRANDS_BY_VERTICAL, META.brand_verticals)
    palette = rng.choice(META.palette_pool)
    font_pair = META.font_pair_locked or rng.choice(META.font_pool)
    sitemap = sample_sitemap(rng, pool=META.sitemap_pool,
                             min_pages=META.sitemap_min, max_pages=META.sitemap_max,
                             first="overview")
    style = StyleSpec(**{k: v for k, v in META.style_axes.items() if isinstance(v, str)})
    return WebsiteSpec(
        slug=f"{META.name}-{seed:04d}",
        archetype=META.archetype, vertical=brand.vertical,
        style=style, palette_seed=palette, font_pair=font_pair,
        difficulty=META.difficulty, sitemap=sitemap, content_seed=seed,
        brand=BrandSpec(**brand.to_brandspec_kwargs()),
        notes=format_notes(DESIGN_NOTES, brand=brand, references=META.style_references),
    )
