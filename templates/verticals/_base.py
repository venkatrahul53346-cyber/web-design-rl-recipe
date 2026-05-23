"""VerticalMeta — what we're building (topic + page hints).

A vertical is independent of visual style. It carries:
- the topic (what kind of website this is)
- per-page hints (what each page should contain)
- which brand-vertical pool to draw from
- the candidate sitemap and bounds
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


VALID_ARCHETYPES = {"A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9",
                    "A10", "A11", "A12"}


@dataclass
class VerticalMeta:
    name: str
    archetype: str
    difficulty: str                          # "easy" | "medium" | "hard"
    topic_description: str                   # ~250 words: what we're building
    page_hints: Dict[str, str]               # {page_name: 1-2 sentence hint}
    sitemap_pool: List[str]                  # 7-10 candidate pages
    sitemap_min: int
    sitemap_max: int
    sitemap_first: str = "index"             # the page that always leads
    brand_verticals: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    density_override: Optional[str] = None   # if set, overrides style.density_default

    # Pattern axes — drive within-pair visual variance. When empty, the LLM
    # picks freely (the pre-pattern-injection behaviour). When populated,
    # sample_spec picks one entry per seed and the design prompt forces the
    # LLM to use that exact pattern. Keep entries short, vivid, and
    # genuinely distinct — two near-equivalents waste a slot.
    hero_patterns: List[str] = field(default_factory=list)
    nav_patterns: List[str] = field(default_factory=list)
    section_arcs: List[str] = field(default_factory=list)
    density_modifiers: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        assert self.archetype in VALID_ARCHETYPES, f"bad archetype {self.archetype}"
        assert self.difficulty in {"easy", "medium", "hard"}, f"bad difficulty {self.difficulty}"
        assert self.sitemap_first in self.sitemap_pool, (
            f"{self.name}: sitemap_first {self.sitemap_first!r} not in sitemap_pool"
        )
        assert 1 <= self.sitemap_min <= self.sitemap_max <= len(self.sitemap_pool), (
            f"{self.name}: sitemap bounds out of range"
        )
