"""A1 SaaS minimal × pastel × hairline-1px × clean-iconographic.

Saturated control: every modern coding agent should ace this. Used to
validate the pipeline plumbing — if oracle scores ~1.0 on this, the
pipeline works.

Design language: lots of whitespace, 1px borders on cards (no shadows),
single accent color from the palette, pale off-white backgrounds.
References: linear.app, attio.com, stripe.com.
"""
from __future__ import annotations

from src.spec import BrandSpec, StyleSpec, WebsiteSpec
from templates import _brands, _fonts, _palettes
from templates._base import (
    TemplateMeta,
    format_notes,
    make_rng,
    sample_brand,
    sample_sitemap,
)


META = TemplateMeta(
    name="saas_minimal",
    archetype="A1",
    difficulty="easy",
    style_axes={
        "density":         "sparse",
        "color_regime":    "pastel",
        "typography":      "geometric-sans",
        "border_language": "hairline-1px",
        "motif":           "clean-iconographic",
    },
    brand_verticals=["saas", "devtools"],
    palette_pool=_palettes.PASTEL_PURPLES_AND_BLUES,
    font_pool=_fonts.GEOMETRIC_SANS,
    font_pair_locked=None,
    sitemap_pool=[
        "index", "features", "pricing", "customers",
        "about", "contact", "integrations",
    ],
    sitemap_min=5,
    sitemap_max=6,
    style_references=["linear.app", "attio.com", "stripe.com"],
)


DESIGN_NOTES = (
    "Design reference: {references_csv}. Lots of whitespace, 1px borders on "
    "cards (no shadows), single accent color from the palette, pale off-white "
    "backgrounds. Avoid centered-on-everything; use generous left-aligned hero "
    "typography. Hero takes ~70vh on first paint. {brand_name}'s tone: "
    "\"{brand_tagline}\" — keep copy crisp, benefit-led, no jargon."
)


def sample_spec(seed: int) -> WebsiteSpec:
    rng = make_rng(seed)
    brand = sample_brand(rng, _brands.BRANDS_BY_VERTICAL, META.brand_verticals)
    palette = rng.choice(META.palette_pool)
    font_pair = META.font_pair_locked or rng.choice(META.font_pool)
    sitemap = sample_sitemap(
        rng, pool=META.sitemap_pool,
        min_pages=META.sitemap_min, max_pages=META.sitemap_max,
    )

    style = StyleSpec(**{
        k: v for k, v in META.style_axes.items() if isinstance(v, str)
    })

    return WebsiteSpec(
        slug=f"{META.name}-{seed:04d}",
        archetype=META.archetype,
        vertical=brand.vertical,
        style=style,
        palette_seed=palette,
        font_pair=font_pair,
        difficulty=META.difficulty,
        sitemap=sitemap,
        content_seed=seed,
        brand=BrandSpec(**brand.to_brandspec_kwargs()),
        notes=format_notes(DESIGN_NOTES, brand=brand,
                           references=META.style_references),
    )
