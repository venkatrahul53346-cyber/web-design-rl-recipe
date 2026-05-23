"""Shared infrastructure for the vertical/style registries.

Public API:

- ``make_rng(seed)`` — single chokepoint for RNG creation.
- ``sample_brand(rng, brands_by_vertical, verticals)`` — pick a
  brand persona compatible with a vertical's allowed brand pools.
- ``sample_sitemap(rng, pool, min_pages, max_pages, first)`` —
  return ``[first, …rng.sample(pool − first, k)]``.
- ``format_notes(template, brand, references)`` — safe ``str.format``
  interpolation of brand-name + references-csv into a notes string.
- ``compose_notes(v, s, brand, sitemap)`` — weave a vertical's
  topic_description + per-page hints + style's notes + references into
  a single prompt-ready string for the LLM compiler.

Note: the old ``TemplateMeta`` class is gone. Verticals use
``templates.verticals._base.VerticalMeta`` and styles use
``templates.styles._base.StyleMeta`` instead.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional


def make_rng(seed: int) -> random.Random:
    return random.Random(seed)


@dataclass
class BrandPersona:
    name: str
    tagline: str
    value_prop: str
    product_category: str
    target_audience: str
    vertical: str

    def to_brandspec_kwargs(self) -> dict:
        return {
            "name": self.name,
            "tagline": self.tagline,
            "value_prop": self.value_prop,
            "product_category": self.product_category,
            "target_audience": self.target_audience,
        }


def sample_brand(rng: random.Random, brands_by_vertical: dict,
                 verticals: List[str]) -> BrandPersona:
    """Pool the brand personas across the listed verticals, pick one.

    Single chokepoint so we never accidentally cross-vertical-leak
    (e.g. restaurant brand on a SaaS template).
    """
    pool: List[BrandPersona] = []
    for v in verticals:
        if v in brands_by_vertical:
            pool.extend(brands_by_vertical[v])
    if not pool:
        raise ValueError(f"no brands for verticals {verticals}")
    return rng.choice(pool)


def sample_sitemap(rng: random.Random, *, pool: List[str],
                   min_pages: int, max_pages: int,
                   first: str = "index") -> List[str]:
    """Return ``[first, ...rng.sample(pool − first, k)]`` with min ≤ N ≤ max."""
    rest = [p for p in pool if p != first]
    k = rng.randint(min_pages, max_pages) - 1
    if k > len(rest):
        k = len(rest)
    return [first] + rng.sample(rest, k=k)


def format_notes(template: str, *, brand: BrandPersona,
                 references: List[str]) -> str:
    """Safe interpolation: only the named placeholders are accepted.
    str.format will raise KeyError on unknown braces — which is what we
    want (catches typos at synth time, not at trial time)."""
    return template.format(
        brand_name=brand.name,
        brand_tagline=brand.tagline,
        references_csv=", ".join(references),
    )


# ---------------------------------------------------------------------------
# Notes composition — vertical's topic + per-page hints + style + image rules.
# ---------------------------------------------------------------------------


IMAGE_RULES = (
    "IMAGE POLICY (HARD CONSTRAINT):\n"
    "- For purely decorative content (hero illustrations, abstract section "
    "  dividers, decorative blobs): use NO `<img>` tags. Use CSS gradients, "
    "  inline SVG, or styled `<div>` blocks with `background-color` / "
    "  `aspect-ratio` instead.\n"
    "- For content-essential photography (product photos, dish photos, hotel "
    "  rooms, portrait avatars, editorial leads), use `<img src=\"X\">` where "
    "  X is EXCLUSIVELY one of these five filenames:\n"
    "    photo-product-1.jpg     (generic product / object — warm tones)\n"
    "    photo-product-2.jpg     (cooler product variant — for grids)\n"
    "    photo-portrait-1.jpg    (generic person — for avatars / team / bylines)\n"
    "    photo-landscape-1.jpg   (generic scene — for hero / hospitality leads)\n"
    "    illustration-abstract.jpg (mesh-gradient — for splash / decorative hero)\n"
    "- Repeating a filename across multiple `<img>` tags is fine.\n"
    "- ANY OTHER `src=` value will be rejected at validation time. No external\n"
    "  URLs, no other filenames, no svg files."
)


def compose_notes(*, v, s, brand: BrandPersona, sitemap: List[str]) -> str:
    """Weave a complete prompt-ready notes string for the LLM compiler.

    Inputs:
      v: VerticalMeta — topic_description, page_hints, references
      s: StyleMeta — style_notes, style_references
      brand: chosen BrandPersona
      sitemap: actual selected pages (so we only emit hints for pages we use)
    """
    page_hint_lines = []
    for page in sitemap:
        hint = v.page_hints.get(page)
        if hint:
            page_hint_lines.append(f"- {page}: {hint}")
    page_hint_block = "\n".join(page_hint_lines) if page_hint_lines else "(no per-page hints)"

    refs_combined = ", ".join(v.references + s.style_references)

    notes = (
        f"WHAT WE'RE BUILDING ({v.name}):\n"
        f"{v.topic_description}\n\n"
        f"BRAND: {brand.name} — \"{brand.tagline}\"\n"
        f"{brand.value_prop}\n\n"
        f"VISUAL LANGUAGE ({s.name}):\n"
        f"{s.style_notes}\n\n"
        f"DESIGN REFERENCES (style + topic): {refs_combined}\n\n"
        f"PER-PAGE GUIDANCE:\n"
        f"{page_hint_block}\n\n"
        f"{IMAGE_RULES}"
    )
    return notes
