"""WebsiteSpec — the canonical input to the synthesis pipeline.

A WebsiteSpec is a structured description of a website. The pipeline:

    WebsiteSpec  →  LLM compiler  →  {filename: HTML/CSS}  →  Harbor task

The schema mirrors TAXONOMY.md §"Schema". Hand-authored for prototype
slots; eventually sampled Cartesianly for scale.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class StyleSpec:
    """Five orthogonal style axes; see TAXONOMY.md."""
    density: str            # sparse | balanced | dense | editorial-narrow
    color_regime: str       # muted-editorial | brand-saturated | dark-native | pastel | glassy | neobrutalist-high-contrast
    typography: str         # geometric-sans | humanist-serif-body | mono-everywhere | display-mixed | variable-display
    border_language: str    # flat | hairline-1px | soft-shadow-rounded | neobrutalist-thick | glassy-blurred
    motif: str              # clean-iconographic | gradient-mesh | abstract-3d | photographic-product | illustration-heavy | data-viz-decor


@dataclass
class BrandSpec:
    """Branded content the LLM should weave into every page."""
    name: str
    tagline: str
    value_prop: str
    product_category: str = ""
    target_audience: str = ""


@dataclass
class WebsiteSpec:
    slug: str                       # e.g. "saas-minimal-001"
    archetype: str                  # A1..A12 from TAXONOMY.md
    vertical: str                   # saas | fintech | devtools | ecom-fashion | ...
    style: StyleSpec
    palette_seed: str               # hex anchor color, e.g. "#8B5CF6"
    font_pair: Tuple[str, str, Optional[str]]  # (display, body, mono_or_None)
    difficulty: str                 # easy | medium | hard
    sitemap: List[str]              # 5-7 page slugs (e.g. ["index","features",...])
    content_seed: int               # for reproducibility
    brand: BrandSpec
    notes: str = ""                 # free-form extra guidance for the LLM
    # Pattern axes — driven by VerticalMeta.{hero,nav,section_arc,density}_patterns.
    # Empty string = no pattern enforced (LLM picks freely).
    hero_pattern: str = ""
    nav_pattern: str = ""
    section_arc: str = ""
    density_modifier: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["font_pair"] = list(self.font_pair)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "WebsiteSpec":
        d = dict(d)
        d["style"] = StyleSpec(**d["style"])
        d["brand"] = BrandSpec(**d["brand"])
        d["font_pair"] = tuple(d["font_pair"])
        return cls(**d)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, s: str) -> "WebsiteSpec":
        return cls.from_dict(json.loads(s))

