"""A3 developer docs × mono-everywhere × hairline-1px × clean-iconographic.

High-signal hard slot. Style references: oxide.computer, rauno.me,
biomejs.dev, supabase docs. Mono typography across the *entire* design
(not just code blocks), hairline borders, warm-neutral background, code
blocks visually distinct via tinted bg + simulated syntax highlighting.

Font is locked to one of the mono pairs (JetBrains/Geist/IBM Plex) —
the typography choice IS part of the template's identity.
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
    name="docs_mono",
    archetype="A3",
    difficulty="hard",
    style_axes={
        "density":         "balanced",
        "color_regime":    "muted-editorial",   # warm neutral, not dark
        "typography":      "mono-everywhere",
        "border_language": "hairline-1px",
        "motif":           "clean-iconographic",
    },
    brand_verticals=["devtools"],
    palette_pool=_palettes.MUTED_EDITORIAL,
    font_pool=_fonts.MONO_EVERYWHERE,
    font_pair_locked=None,                       # sample from the mono pool
    sitemap_pool=[
        "index", "getting-started", "api-reference",
        "guides", "examples", "changelog",
    ],
    sitemap_min=6,
    sitemap_max=6,                               # docs slate is fixed shape
    style_references=["oxide.computer/docs", "biomejs.dev", "rauno.me"],
)


DESIGN_NOTES = (
    "Design reference: {references_csv}. "
    "Mono typeface across ALL text — headings, body, code, captions. "
    "Hairline 1px borders, NO box-shadows, NO rounded corners (or 0–2px "
    "max). Background: warm off-white (#FBF8F3 or similar), text: dark "
    "ink (#1A1815). Accent (the palette anchor) used sparingly for the "
    "logomark, active link state, and inline-code highlight.\n\n"
    "Layout: 3-pane on docs pages — left rail navigation tree "
    "(getting-started / api-reference / guides / examples), centre "
    "prose+code (~720px max), right rail page TOC. Index can be 2-pane "
    "or single-column.\n\n"
    "Code blocks must be VISUALLY DISTINCT — slightly tinted background "
    "(#F2EFE7), 1px border on top+bottom, mono code with simulated "
    "syntax highlighting via spans/colors (e.g. keywords in #6E5BCB, "
    "strings in #007E5A, comments in #888). Prose-style explanations "
    "between code blocks.\n\n"
    "Each page should have content appropriate to its purpose: "
    "getting-started has install/quickstart code, api-reference has "
    "parameter tables and response examples, guides has step-by-step "
    "recipes, examples has full integration code snippets, changelog is "
    "a chronological list of versioned entries. AVOID generic 'feature "
    "one / feature two' filler.\n\n"
    "{brand_name} is the product name; \"{brand_tagline}\" is the tagline."
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
