"""Template registry — vertical × style combination.

Two independent registries, combined by a compatibility matrix:
- ``VERTICALS`` (templates/verticals/) carries topic, page hints,
  brand-vertical constraints, sitemap.
- ``STYLES`` (templates/styles/) carries the locked style axes
  (color_regime × typography × border_language × motif), palette
  pool, font pool.
- ``COMPATIBLE_STYLES`` (templates/compatibility.py) lists which
  (vertical, style) pairs are visually plausible.

Public API:
    VERTICALS, STYLES, COMPATIBLE_STYLES
    sample_spec(vertical_name, style_name, seed) -> WebsiteSpec
    random_spec(seed) -> tuple[str, str, WebsiteSpec]
    is_compatible / list_compatible_styles / all_valid_pairs / random_compatible_pair
"""
from __future__ import annotations

import random
from typing import Tuple

from src.spec import BrandSpec, StyleSpec, WebsiteSpec
from templates._base import (
    BrandPersona,
    compose_notes,
    format_notes,
    make_rng,
    sample_brand,
    sample_sitemap,
)
from templates._brands import BRANDS_BY_VERTICAL
from templates.compatibility import (
    COMPATIBLE_STYLES,
    all_valid_pairs,
    is_compatible,
    list_compatible_styles,
    random_compatible_pair,
)
from templates.styles import STYLES
from templates.verticals import VERTICALS


__all__ = [
    "VERTICALS", "STYLES", "COMPATIBLE_STYLES",
    "sample_spec", "random_spec",
    "is_compatible", "list_compatible_styles",
    "all_valid_pairs", "random_compatible_pair",
    "BrandPersona", "compose_notes", "format_notes",
    "make_rng", "sample_brand", "sample_sitemap",
]


def sample_spec(vertical_name: str, style_name: str, seed: int) -> WebsiteSpec:
    """Sample a deterministic WebsiteSpec from a (vertical, style) pair.

    Raises ``ValueError`` if the pair is not in ``COMPATIBLE_STYLES``.
    """
    if not is_compatible(vertical_name, style_name):
        raise ValueError(
            f"({vertical_name}, {style_name}) is not in COMPATIBLE_STYLES. "
            f"Allowed styles for {vertical_name}: "
            f"{list_compatible_styles(vertical_name)}"
        )
    if vertical_name not in VERTICALS:
        raise ValueError(f"unknown vertical {vertical_name!r}")
    if style_name not in STYLES:
        raise ValueError(f"unknown style {style_name!r}")

    v = VERTICALS[vertical_name].META
    s = STYLES[style_name].META
    rng = make_rng(seed)

    brand = sample_brand(rng, BRANDS_BY_VERTICAL, v.brand_verticals)
    palette = rng.choice(s.palette_pool)
    font_pair = s.font_pair_locked or rng.choice(s.font_pool)
    sitemap = sample_sitemap(
        rng, pool=v.sitemap_pool,
        min_pages=v.sitemap_min, max_pages=v.sitemap_max,
        first=v.sitemap_first,
    )

    # Pattern injection — pick one of each axis if the vertical defines them.
    # Empty axis lists mean "no pattern enforced" (the pre-injection default).
    hero_pattern = rng.choice(v.hero_patterns) if v.hero_patterns else ""
    nav_pattern = rng.choice(v.nav_patterns) if v.nav_patterns else ""
    section_arc = rng.choice(v.section_arcs) if v.section_arcs else ""
    density_modifier = rng.choice(v.density_modifiers) if v.density_modifiers else ""

    style_axes = StyleSpec(
        density=v.density_override or s.density_default,
        color_regime=s.color_regime,
        typography=s.typography,
        border_language=s.border_language,
        motif=s.motif,
    )
    notes = compose_notes(v=v, s=s, brand=brand, sitemap=sitemap)

    return WebsiteSpec(
        slug=f"{vertical_name}__{style_name}-{seed:04d}",
        archetype=v.archetype,
        vertical=brand.vertical,
        style=style_axes,
        palette_seed=palette,
        font_pair=font_pair,
        difficulty=v.difficulty,
        sitemap=sitemap,
        content_seed=seed,
        brand=BrandSpec(**brand.to_brandspec_kwargs()),
        notes=notes,
        hero_pattern=hero_pattern,
        nav_pattern=nav_pattern,
        section_arc=section_arc,
        density_modifier=density_modifier,
    )


def random_spec(seed: int) -> Tuple[str, str, WebsiteSpec]:
    """Pick a random compatible (vertical, style) pair, sample a spec.

    Returns ``(vertical_name, style_name, spec)`` so the caller can log
    the selection. Both pair-selection and spec-sampling use the same
    seed; if independent draws are needed in future, derive sub-seeds.
    """
    rng = random.Random(seed)
    v_name, s_name = random_compatible_pair(rng)
    return v_name, s_name, sample_spec(v_name, s_name, seed)
