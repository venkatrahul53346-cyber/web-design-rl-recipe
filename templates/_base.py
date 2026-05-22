"""Shared infrastructure for the template registry.

Each template module under ``templates/`` defines:

- ``META: TemplateMeta`` — locked vs sampled axes, brand verticals, pools.
- ``DESIGN_NOTES: str`` — locked prompt-engineering payload (may contain
  ``{brand_name}`` / ``{references_csv}`` placeholders, interpolated via
  :func:`format_notes`).
- ``sample_spec(seed: int) -> WebsiteSpec`` — deterministic sampler.

The registry that maps template names → modules lives in
``templates/__init__.py`` (an explicit dict, no autoglob).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# Single chokepoint for determinism. Future swap (e.g. counter-based RNG)
# is one line. Every template imports ``make_rng`` from here.
def make_rng(seed: int) -> random.Random:
    return random.Random(seed)


@dataclass
class TemplateMeta:
    """Description of a template's design space.

    A template is one tightly-scoped (archetype × locked-style) cell.
    Some style axes are locked (they define what the template *is*);
    others can be left open for the sampler to fill in.

    Fields with `list[...]` typing are sample pools; fields with scalar
    typing are locked. The ``style_axes`` dict is the only place that
    carries both — a string value means locked, a list value means
    "sample one per seed".
    """
    name: str                              # registry key, e.g. "saas_minimal"
    archetype: str                         # "A1".."A12"
    difficulty: str                        # "easy" | "medium" | "hard"
    style_axes: dict                       # axis -> str (locked) | list[str] (sample)
    brand_verticals: List[str]             # keys into _brands.BRANDS_BY_VERTICAL
    palette_pool: List[str]                # hex anchor colors
    font_pool: List[Tuple[str, str, Optional[str]]]  # (display, body, mono?)
    sitemap_pool: List[str]
    sitemap_min: int
    sitemap_max: int
    style_references: List[str]            # text descriptors only (e.g. "linear.app")
    font_pair_locked: Optional[Tuple[str, str, Optional[str]]] = None  # None = sample


@dataclass
class BrandPersona:
    """A pre-curated brand identity. Lives in ``_brands.py``."""
    name: str
    tagline: str
    value_prop: str
    product_category: str
    target_audience: str
    vertical: str       # mirrors the BRANDS_BY_VERTICAL key

    def to_brandspec_kwargs(self) -> dict:
        """Map to BrandSpec(...) kwargs (BrandSpec doesn't carry vertical)."""
        return {
            "name": self.name,
            "tagline": self.tagline,
            "value_prop": self.value_prop,
            "product_category": self.product_category,
            "target_audience": self.target_audience,
        }


def format_notes(template_notes: str, *, brand: BrandPersona,
                 references: List[str]) -> str:
    """Safe interpolation of template DESIGN_NOTES.

    Supports a small fixed set of placeholders:

    - ``{brand_name}``
    - ``{brand_tagline}``
    - ``{references_csv}`` — comma-separated style-reference list

    No f-string eval, no ``locals()`` injection. If a template's notes
    contain a brace that isn't one of these keys, ``str.format`` will
    raise ``KeyError`` — which is what we want (catches typos at synth
    time, not at trial time).
    """
    return template_notes.format(
        brand_name=brand.name,
        brand_tagline=brand.tagline,
        references_csv=", ".join(references),
    )


def sample_sitemap(rng: random.Random, *, pool: List[str],
                   min_pages: int, max_pages: int,
                   first: str = "index") -> List[str]:
    """Return ``[first, ...rng.sample(pool - first, k)]`` with ``min ≤ N ≤ max``.

    Centralises the "always lead with index" + "random subset" idiom that
    every template uses. ``first`` may be any page name (e.g. "signup" for
    auth flows where there's no /index).
    """
    rest = [p for p in pool if p != first]
    k = rng.randint(min_pages, max_pages) - 1
    if k > len(rest):
        k = len(rest)
    return [first] + rng.sample(rest, k=k)


def sample_brand(rng: random.Random, brands_by_vertical: dict,
                 verticals: List[str]) -> BrandPersona:
    """Pool ``brands_by_vertical[v]`` for each ``v`` in ``verticals``,
    pick one. Single chokepoint so we never accidentally cross-vertical-
    leak (e.g. restaurant brand on a SaaS template)."""
    pool: List[BrandPersona] = []
    for v in verticals:
        pool.extend(brands_by_vertical[v])
    if not pool:
        raise ValueError(f"no brands for verticals {verticals}")
    return rng.choice(pool)
