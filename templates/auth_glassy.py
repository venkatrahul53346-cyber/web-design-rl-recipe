"""A12 auth × pastel × glassy-blurred × clean-iconographic.

Saturated control. Centered cards on a soft gradient with frosted-glass
treatment — clerk.dev, vercel/supabase login. Sparse by structure.
"""
from __future__ import annotations

from src.spec import BrandSpec, StyleSpec, WebsiteSpec
from templates import _brands, _fonts, _palettes
from templates._base import (
    TemplateMeta, format_notes, make_rng, sample_brand, sample_sitemap,
)


META = TemplateMeta(
    name="auth_glassy",
    archetype="A12",
    difficulty="easy",
    style_axes={
        "density":         "sparse",
        "color_regime":    "pastel",
        "typography":      "geometric-sans",
        "border_language": "glassy-blurred",
        "motif":           "clean-iconographic",
    },
    brand_verticals=["saas", "devtools", "fintech", "ai-product"],
    palette_pool=_palettes.PASTEL_PURPLES_AND_BLUES + _palettes.GLASSY,
    font_pool=_fonts.GEOMETRIC_SANS,
    font_pair_locked=None,
    sitemap_pool=["signup", "login", "verify", "onboarding-step-1",
                  "onboarding-step-2", "dashboard-empty"],
    sitemap_min=5,
    sitemap_max=6,
    style_references=["clerk.dev", "vercel.com/login", "supabase.com/dashboard/sign-in"],
)

DESIGN_NOTES = (
    "Design reference: {references_csv}. Backgrounds are soft gradient "
    "fields (palette anchor at 8-12% saturation, blending to a light "
    "neutral). Auth content lives in centered cards (~420px wide) with a "
    "frosted-glass effect: subtle backdrop-filter blur, semi-transparent "
    "white background (rgba(255,255,255,0.7)), 1px translucent border.\n\n"
    "Each form: brand mark on top, page title (e.g. 'Sign up for "
    "{brand_name}'), 1-2 social-login buttons with provider icons, divider "
    "(\"or continue with email\"), 2-3 form fields with subtle backgrounds, "
    "primary CTA filled with the palette anchor, footer link to the other "
    "auth page.\n\n"
    "Onboarding-step pages: same card treatment + a 3-dot or progress-bar "
    "indicator showing 'step N of M'. Dashboard-empty: centered icon + "
    "headline + sub-copy + primary CTA, NO sidebar yet (user is fresh).\n\n"
    "Avoid: heavy shadows, busy backgrounds, opaque white cards (defeats "
    "glassy), oversaturated gradients (defeats pastel)."
)


def sample_spec(seed: int) -> WebsiteSpec:
    rng = make_rng(seed)
    brand = sample_brand(rng, _brands.BRANDS_BY_VERTICAL, META.brand_verticals)
    palette = rng.choice(META.palette_pool)
    font_pair = META.font_pair_locked or rng.choice(META.font_pool)
    sitemap = sample_sitemap(rng, pool=META.sitemap_pool,
                             min_pages=META.sitemap_min, max_pages=META.sitemap_max,
                             first="signup")
    style = StyleSpec(**{k: v for k, v in META.style_axes.items() if isinstance(v, str)})
    return WebsiteSpec(
        slug=f"{META.name}-{seed:04d}",
        archetype=META.archetype, vertical=brand.vertical,
        style=style, palette_seed=palette, font_pair=font_pair,
        difficulty=META.difficulty, sitemap=sitemap, content_seed=seed,
        brand=BrandSpec(**brand.to_brandspec_kwargs()),
        notes=format_notes(DESIGN_NOTES, brand=brand, references=META.style_references),
    )
