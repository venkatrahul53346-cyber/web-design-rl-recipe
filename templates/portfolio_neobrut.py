"""A7 portfolio × display-mixed × neobrutalist-thick × variable-display.

High-signal hard slot. Big-typography hero, opinionated grids, motion-
implied. basicagency.com, locomotive.ca.
"""
from __future__ import annotations

from src.spec import BrandSpec, StyleSpec, WebsiteSpec
from templates import _brands, _fonts, _palettes
from templates._base import (
    TemplateMeta, format_notes, make_rng, sample_brand, sample_sitemap,
)


META = TemplateMeta(
    name="portfolio_neobrut",
    archetype="A7",
    difficulty="hard",
    style_axes={
        "density":         "balanced",
        "color_regime":    "neobrutalist-high-contrast",
        "typography":      "variable-display",
        "border_language": "neobrutalist-thick",
        "motif":           "illustration-heavy",
    },
    brand_verticals=["agency"],
    palette_pool=_palettes.NEOBRUTALIST_HIGH_CONTRAST,
    font_pool=_fonts.VARIABLE_DISPLAY,
    font_pair_locked=None,
    sitemap_pool=["index", "work-index", "case-study-A", "case-study-B", "about", "contact"],
    sitemap_min=6,
    sitemap_max=6,
    style_references=["basicagency.com", "locomotive.ca", "areweb.studio"],
)

DESIGN_NOTES = (
    "Design reference: {references_csv}. Background a single bold color "
    "from the palette OR pure off-white (#FAFAFA). Borders: solid 2-3px "
    "BLACK on every card / button / image frame. Drop shadows are "
    "BLACK and offset hard (translateX 4px, translateY 4px), no blur. "
    "Buttons translate-on-hover into their shadow. NO gradients, NO "
    "rounded corners over 4px.\n\n"
    "Typography is the lead character: oversized display headlines "
    "(120-180px on desktop), variable-axis treatment if the font supports "
    "it, mixed weights and slants for visual rhythm. Body type small and "
    "tight (14-15px). Color is structural: bold blocks of yellow / red / "
    "blue used as backgrounds for sections.\n\n"
    "Index: oversized hero word/phrase that takes a third of the screen, "
    "case-study tiles in an asymmetric grid (3 of different sizes, with "
    "captions below). Work-index: more tiles, possibly with hover-state "
    "image-swap implied by an enlarged thumbnail. Case-study pages: "
    "title, client/year/role meta block, problem statement, hero image, "
    "approach, outcome with images interspersed. About: agency manifesto "
    "(short prose), team grid (4-8 placeholder people), services list. "
    "Contact: oversized email link, address, social links.\n\n"
    "{brand_name} is a design studio — \"{brand_tagline}\". Use as the "
    "wordmark in heavy black + a single accent color. Avoid: corporate "
    "cleanness, even spacing on all sides of every block, default "
    "Tailwind shadows."
)


def sample_spec(seed: int) -> WebsiteSpec:
    rng = make_rng(seed)
    brand = sample_brand(rng, _brands.BRANDS_BY_VERTICAL, META.brand_verticals)
    palette = rng.choice(META.palette_pool)
    font_pair = META.font_pair_locked or rng.choice(META.font_pool)
    sitemap = sample_sitemap(rng, pool=META.sitemap_pool,
                             min_pages=META.sitemap_min, max_pages=META.sitemap_max)
    style = StyleSpec(**{k: v for k, v in META.style_axes.items() if isinstance(v, str)})
    return WebsiteSpec(
        slug=f"{META.name}-{seed:04d}",
        archetype=META.archetype, vertical=brand.vertical,
        style=style, palette_seed=palette, font_pair=font_pair,
        difficulty=META.difficulty, sitemap=sitemap, content_seed=seed,
        brand=BrandSpec(**brand.to_brandspec_kwargs()),
        notes=format_notes(DESIGN_NOTES, brand=brand, references=META.style_references),
    )
