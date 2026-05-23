"""Palette anchor colors grouped by ``style.color_regime``.

Each entry is a single hex anchor (the brand's primary accent). The
LLM design pass will derive a full palette around it (neutrals, hover
states, etc.). We sample the anchor only.
"""
from __future__ import annotations

from typing import Dict, List


# Pastel: soft, low-saturation accents on pale off-white.
PASTEL_PURPLES_AND_BLUES: List[str] = [
    "#8B5CF6",   # soft purple (slot 1's original)
    "#7C3AED",   # deeper violet
    "#6366F1",   # indigo
    "#0EA5E9",   # sky blue
    "#14B8A6",   # muted teal
]

# Muted-editorial: warm/cool low-chroma editorial accents.
MUTED_EDITORIAL: List[str] = [
    "#D04A02",   # deep orange (slot 4's original tessera-brand)
    "#7C2D12",   # rust brown
    "#854D0E",   # warm ochre
    "#3F4856",   # cool slate
    "#5B5063",   # mauve grey
]

# Dark-native: jewel-tone accents that survive on dark backgrounds.
DARK_NATIVE: List[str] = [
    "#22D3EE",   # cyan
    "#A78BFA",   # bright violet
    "#F59E0B",   # amber
    "#EF4444",   # red
    "#10B981",   # emerald
]


PALETTES_BY_REGIME: Dict[str, List[str]] = {
    "pastel":          PASTEL_PURPLES_AND_BLUES,
    "muted-editorial": MUTED_EDITORIAL,
    "dark-native":     DARK_NATIVE,
}


# Glassy: high-saturation accents that look right on a frosted-glass card.
GLASSY: List[str] = [
    "#A78BFA",   # bright violet
    "#60A5FA",   # bright blue
    "#F472B6",   # bright pink
    "#34D399",   # bright emerald
    "#FBBF24",   # warm amber
]

# Neobrutalist high-contrast: strong primary anchors, pair with thick black borders.
NEOBRUTALIST_HIGH_CONTRAST: List[str] = [
    "#FFD43B",   # caution yellow
    "#FF6B35",   # signal orange
    "#FF3B5C",   # cherry red
    "#3B82F6",   # bold blue
    "#22C55E",   # bold green
]

# Brand-saturated: vivid mid-saturation accents typical of modern SaaS hero sections.
BRAND_SATURATED: List[str] = [
    "#FF3D71",   # magenta
    "#7C3AED",   # violet
    "#0E7C66",   # forest teal
    "#0F4C81",   # navy
    "#E11D48",   # rose
]


PALETTES_BY_REGIME["glassy"]                       = GLASSY
PALETTES_BY_REGIME["neobrutalist-high-contrast"]   = NEOBRUTALIST_HIGH_CONTRAST
PALETTES_BY_REGIME["brand-saturated"]              = BRAND_SATURATED


# Editorial-dark: warm neutrals on near-black for night-mode longform.
EDITORIAL_DARK: List[str] = [
    "#C9A36E",   # warm amber
    "#A88A5C",   # ochre
    "#D4B07C",   # honey
    "#B07C5A",   # terracotta
    "#8E7344",   # olive-mustard
]

# Neon (crypto / web3): glowing accents on near-black surfaces.
NEON: List[str] = [
    "#7DF9FF",   # electric cyan
    "#FF61D2",   # magenta neon
    "#A6FF7E",   # acid green
    "#7C5BFF",   # ultraviolet
    "#FFD24A",   # amber neon
]


PALETTES_BY_REGIME["editorial-dark"] = EDITORIAL_DARK
PALETTES_BY_REGIME["neon"]           = NEON
