"""A6 editorial × humanist-serif-body × editorial-narrow × photographic.

High-signal hard slot. Longform reading sites — every.to, theverge
features. Serif body, narrow measure (~65ch), pull quotes, drop caps,
photographic lead images.
"""
from __future__ import annotations

from src.spec import BrandSpec, StyleSpec, WebsiteSpec
from templates import _brands, _fonts, _palettes
from templates._base import (
    TemplateMeta, format_notes, make_rng, sample_brand, sample_sitemap,
)


META = TemplateMeta(
    name="editorial_serif",
    archetype="A6",
    difficulty="hard",
    style_axes={
        "density":         "editorial-narrow",
        "color_regime":    "muted-editorial",
        "typography":      "humanist-serif-body",
        "border_language": "flat",
        "motif":           "photographic-product",
    },
    brand_verticals=["media"],
    palette_pool=_palettes.MUTED_EDITORIAL,
    font_pool=_fonts.HUMANIST_SERIF_BODY,
    font_pair_locked=None,
    sitemap_pool=["index", "article-A", "article-B", "author-page", "tag-page", "about"],
    sitemap_min=6,
    sitemap_max=6,
    style_references=["every.to", "theverge.com/features", "harpers.org"],
)

DESIGN_NOTES = (
    "Design reference: {references_csv}. Serif body type at 18-19px, "
    "line-height 1.6, measure ~65ch (~640-680px). Body in a humanist "
    "serif (Tiempos, Source Serif, Lora). Display headlines in the same "
    "family at heavier weight, OR a paired display serif. Generous "
    "vertical rhythm — articles breathe.\n\n"
    "Index: editorial cover with hero article (large image + headline + "
    "dek + author/date), then 4-6 secondary articles in a sparse grid. "
    "Article pages: lead photo (full-bleed or wide), headline (very "
    "large, ~64-80px), dek/standfirst (lighter weight, ~22px), byline + "
    "date, then body. First paragraph may use a drop cap or all-caps "
    "lede. One pull quote partway through (italic, large, indented). "
    "End with a short author bio and a 'related reads' module of 2-3 "
    "links. NO sidebars during article body — keep the measure narrow.\n\n"
    "Author/tag pages: simple list of articles by that author/tag, "
    "with thumbnails. About: short masthead — who runs the publication, "
    "how often it publishes, where to subscribe.\n\n"
    "Use rick.jpg as the placeholder for any photographic image. "
    "Background warm off-white (#FBF8F3 or pure #FFF), text dark ink "
    "(#1A1815). Accent only for links + tag chips. {brand_name} is the "
    "publication name; \"{brand_tagline}\" is the masthead line. "
    "Avoid: sans-serif body (defeats template), centered text blocks, "
    "cards with shadows."
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
