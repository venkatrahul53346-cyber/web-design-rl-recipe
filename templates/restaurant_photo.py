"""A11 restaurant × photographic-product × display-mixed × muted-editorial.

High-signal hard slot. Photographic hero, serif display, menu sections,
location/hours. sweetgreen.com, ace hotels, modern indie restaurants.
"""
from __future__ import annotations

from src.spec import BrandSpec, StyleSpec, WebsiteSpec
from templates import _brands, _fonts, _palettes
from templates._base import (
    TemplateMeta, format_notes, make_rng, sample_brand, sample_sitemap,
)


META = TemplateMeta(
    name="restaurant_photo",
    archetype="A11",
    difficulty="hard",
    style_axes={
        "density":         "balanced",
        "color_regime":    "muted-editorial",
        "typography":      "display-mixed",
        "border_language": "flat",
        "motif":           "photographic-product",
    },
    brand_verticals=["hospitality"],
    palette_pool=_palettes.MUTED_EDITORIAL,
    font_pool=_fonts.DISPLAY_MIXED,
    font_pair_locked=None,
    sitemap_pool=["index", "menu", "reservations", "about", "location", "press"],
    sitemap_min=6,
    sitemap_max=6,
    style_references=["acehotel.com", "lestrop.com", "sister-cities.com"],
)

DESIGN_NOTES = (
    "Design reference: {references_csv}. Warm neutral background "
    "(#F4EFE7 / #FBF7F0). Photography is essential — full-bleed "
    "hero on index (use rick.jpg as the placeholder). Display "
    "headlines in a serif or display face (Migra / PP Editorial / "
    "Druk Wide), body in a clean sans for legibility. Soft, "
    "saturated accent (#7C2D12 rust or #854D0E ochre) used for "
    "links + primary CTA underline.\n\n"
    "Index: full-bleed hero photograph + restaurant/hotel name in "
    "large display, dek with location + opening hours. Below: a "
    "section that introduces the place (prose paragraph + secondary "
    "photograph), a glimpse of the menu (3-4 dishes with photos and "
    "prices), opening hours table.\n\n"
    "Menu page: sections (Starters / Mains / Drinks / Dessert), each "
    "a flat list — dish name (display weight), description (italic "
    "or smaller), price right-aligned with leader dots or whitespace. "
    "Reservations: minimal form — date / time / party-size / contact "
    "info / dietary notes textarea / submit. About: founder/chef bio + "
    "philosophy paragraph + photographic interludes. Location: address, "
    "embedded-map placeholder (a styled rectangle), hours table by day "
    "of week, parking/transit notes. Press: list of media mentions with "
    "publication name + headline + date + outbound link.\n\n"
    "{brand_name} is a hospitality business — \"{brand_tagline}\". "
    "Avoid: SaaS-style feature cards, neon palettes, generic stock "
    "photography placeholders. Use the dish/restaurant tone."
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
