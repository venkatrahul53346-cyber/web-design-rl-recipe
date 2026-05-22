"""A8 pricing-centric × dark-native × hairline-1px × clean-iconographic.

Saturated control. Pricing matrices on dark backgrounds with a single
glowing accent — vercel.com/pricing, linear.app/pricing in dark mode.
Saturated archetype because models reliably nail tier-comparison tables.
"""
from __future__ import annotations

from src.spec import BrandSpec, StyleSpec, WebsiteSpec
from templates import _brands, _fonts, _palettes
from templates._base import (
    TemplateMeta, format_notes, make_rng, sample_brand, sample_sitemap,
)


META = TemplateMeta(
    name="pricing_dark",
    archetype="A8",
    difficulty="easy",
    style_axes={
        "density":         "balanced",
        "color_regime":    "dark-native",
        "typography":      "geometric-sans",
        "border_language": "hairline-1px",
        "motif":           "clean-iconographic",
    },
    brand_verticals=["saas", "devtools", "ai-product"],
    palette_pool=_palettes.DARK_NATIVE,
    font_pool=_fonts.GEOMETRIC_SANS,
    font_pair_locked=None,
    sitemap_pool=["index", "pricing", "compare", "faq", "customers", "contact", "enterprise"],
    sitemap_min=5,
    sitemap_max=6,
    style_references=["linear.app/pricing", "vercel.com/pricing", "stripe.com/pricing"],
)

DESIGN_NOTES = (
    "Design reference: {references_csv}. Background near-black "
    "(#0A0A0B / #111114), text near-white (#F5F5F7) at high contrast. "
    "Single accent color from the palette used sparingly: highlighted "
    "tier card, primary CTA, hover state. Body weight 500 — slightly "
    "heavier than typical for legibility on dark.\n\n"
    "Pricing page is the centerpiece: 3 tier cards (Free / Pro / Enterprise), "
    "side-by-side, with the middle one outlined with a 1px accent stroke and "
    "marked 'Recommended' or similar. Each card: tier name, price (large), "
    "1-line description, 6-10 feature bullets with check or dot glyphs, "
    "primary CTA. Hairline 1px borders only — no shadows, no rounded "
    "corners beyond 6-8px.\n\n"
    "Compare page: full feature-vs-tier matrix, sticky header row, hairline "
    "1px row separators. FAQ: collapsed accordion list, ~10 questions with "
    "concise answers.\n\n"
    "{brand_name}'s tagline: \"{brand_tagline}\". Use the value prop in the "
    "hero. Avoid saturated gradients. Avoid feature checkboxes that look "
    "like form inputs."
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
