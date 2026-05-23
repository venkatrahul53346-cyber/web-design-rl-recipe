"""StyleMeta — how it looks (visual language, palette, fonts).

A style is independent of topic. It locks the four style axes
(color_regime × typography × border_language × motif) — those bundled
choices ARE the style's identity. Within those axes, palette anchor
and font pair are sampled per seed.

A density default is provided; verticals can override (e.g.
dashboard_app forces density=dense regardless of style).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


VALID_DENSITIES = {"sparse", "balanced", "dense", "editorial-narrow"}
VALID_COLOR_REGIMES = {
    "muted-editorial", "brand-saturated", "dark-native", "pastel",
    "glassy", "neobrutalist-high-contrast", "editorial-dark", "neon",
}
VALID_TYPOGRAPHIES = {
    "geometric-sans", "humanist-serif-body", "mono-everywhere",
    "display-mixed", "variable-display",
}
VALID_BORDERS = {
    "flat", "hairline-1px", "soft-shadow-rounded",
    "neobrutalist-thick", "glassy-blurred",
}
VALID_MOTIFS = {
    "clean-iconographic", "gradient-mesh", "abstract-3d",
    "photographic-product", "illustration-heavy", "data-viz-decor",
}


@dataclass
class StyleMeta:
    name: str
    color_regime: str
    typography: str
    border_language: str
    motif: str
    density_default: str
    palette_pool: List[str]                  # hex anchors from the regime
    font_pool: List[Tuple[str, str, Optional[str]]]   # (display, body, mono?)
    style_notes: str                         # ~200 words visual language
    style_references: List[str] = field(default_factory=list)
    font_pair_locked: Optional[Tuple[str, str, Optional[str]]] = None

    def __post_init__(self) -> None:
        assert self.color_regime in VALID_COLOR_REGIMES, f"bad regime {self.color_regime}"
        assert self.typography in VALID_TYPOGRAPHIES, f"bad typography {self.typography}"
        assert self.border_language in VALID_BORDERS, f"bad border {self.border_language}"
        assert self.motif in VALID_MOTIFS, f"bad motif {self.motif}"
        assert self.density_default in VALID_DENSITIES, f"bad density {self.density_default}"
        assert self.palette_pool, f"{self.name}: empty palette_pool"
        if self.font_pair_locked is None:
            assert self.font_pool, f"{self.name}: empty font_pool and no lock"
