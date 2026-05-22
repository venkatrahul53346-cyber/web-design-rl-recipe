"""A9 single-product splash × abstract-3d × dark-native × variable-display.

High-signal hard slot. One-page narrative, scroll-driven, oversized
type, cinematic. rabbit.tech, humane.com.
"""
from __future__ import annotations

from src.spec import BrandSpec, StyleSpec, WebsiteSpec
from templates import _brands, _fonts, _palettes
from templates._base import (
    TemplateMeta, format_notes, make_rng, sample_brand, sample_sitemap,
)


META = TemplateMeta(
    name="splash_3d",
    archetype="A9",
    difficulty="hard",
    style_axes={
        "density":         "sparse",
        "color_regime":    "dark-native",
        "typography":      "variable-display",
        "border_language": "flat",
        "motif":           "abstract-3d",
    },
    brand_verticals=["ai-product"],
    palette_pool=_palettes.DARK_NATIVE,
    font_pool=_fonts.VARIABLE_DISPLAY,
    font_pair_locked=None,
    sitemap_pool=["index", "story", "specs", "preorder", "faq", "press"],
    sitemap_min=6,
    sitemap_max=6,
    style_references=["rabbit.tech", "humane.com", "teenage.engineering"],
)

DESIGN_NOTES = (
    "Design reference: {references_csv}. Background near-pure-black "
    "(#000 / #050505). The product is the show: oversized hero image "
    "(use rick.jpg as the placeholder, present it like a hero render — "
    "centered, ample negative space around it). Display headlines very "
    "large (120-200px) in a variable-axis cut. Body type small and "
    "spaced. Accent color appears as a single glow / underline / dot — "
    "never as filled card backgrounds.\n\n"
    "Index: hero is product image + 1-2 line tagline, no CTA above the "
    "fold (the page itself is the CTA). Below, scroll-revealed sections "
    "of feature beats — each section a single image + a single short "
    "block of copy, alternating image-left / image-right. Story page: "
    "long-form narrative about the product, oversized type, photographic "
    "interludes. Specs page: technical spec table — dimensions, weight, "
    "battery, materials — set in tabular figures, hairline dividers, no "
    "decorations. Preorder: minimal form — email + (optional) shipping "
    "country, oversized CTA, FAQ link. FAQ: vertical accordion. Press: "
    "press logos cluster + recent media mentions list + press contact.\n\n"
    "{brand_name} is the product name; \"{brand_tagline}\" is the "
    "tagline. Avoid: shadcn-style card grids, multiple primary CTAs "
    "above the fold, sales-y discount language, light backgrounds."
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
