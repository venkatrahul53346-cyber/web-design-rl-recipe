"""A5 e-commerce × pastel × hairline-1px × photographic-product.

High-signal hard slot. Product grid + filter rail + large product
photography. allbirds.com, gentlemonster.com.
"""
from __future__ import annotations

from src.spec import BrandSpec, StyleSpec, WebsiteSpec
from templates import _brands, _fonts, _palettes
from templates._base import (
    TemplateMeta, format_notes, make_rng, sample_brand, sample_sitemap,
)


META = TemplateMeta(
    name="ecom_pastel",
    archetype="A5",
    difficulty="hard",
    style_axes={
        "density":         "balanced",
        "color_regime":    "pastel",
        "typography":      "geometric-sans",
        "border_language": "hairline-1px",
        "motif":           "photographic-product",
    },
    brand_verticals=["ecom-fashion"],
    palette_pool=_palettes.PASTEL_PURPLES_AND_BLUES,
    font_pool=_fonts.GEOMETRIC_SANS,
    font_pair_locked=None,
    sitemap_pool=["index", "collection", "PDP", "cart", "about", "journal"],
    sitemap_min=6,
    sitemap_max=6,
    style_references=["allbirds.com", "everlane.com", "muji.com"],
)

DESIGN_NOTES = (
    "Design reference: {references_csv}. Pale, warm-neutral background "
    "(#FAF8F5 / #F7F5F0). Photography is the lead — full-bleed hero "
    "image on index, large product photos on PDP. Use rick.jpg as the "
    "placeholder for product photography. Hairline 1px dividers, no "
    "shadows.\n\n"
    "Index: large editorial hero with full-bleed product image and a "
    "minimal headline + CTA, then a 'shop by category' grid (3-4 tiles), "
    "then a featured-products row. Collection page (PLP): left rail of "
    "filters (size, color, category, price range — checkbox lists with "
    "hairline dividers), right grid of products (3-4 col). Each product "
    "tile: image, name, price, optional swatch row. PDP: large image "
    "left, product info right (name, price, short description, size "
    "selector, color swatches, primary CTA, longer description "
    "accordion). Cart: line items table, subtotal/shipping/total stack, "
    "checkout CTA. About: brand story prose with photography. Journal: "
    "blog-style list of editorial posts.\n\n"
    "{brand_name}'s tone: \"{brand_tagline}\". Quiet, considered, no "
    "discount-driven urgency. Avoid: carousel arrows, bright sale "
    "banners, shadowed cards (defeats hairline-1px), Comic-Sans-style "
    "informal typography."
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
