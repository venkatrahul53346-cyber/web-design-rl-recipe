"""Font pairs grouped by ``style.typography``.

Each entry is a ``(display, body, mono_or_None)`` tuple matching
``WebsiteSpec.font_pair``. The LLM uses these as ``@import`` anchors;
templates may also lock to a specific stack via
``META.font_pair_locked`` when typography choice is part of the
template's identity (e.g. devdocs locks to JetBrains Mono).
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple


GEOMETRIC_SANS: List[Tuple[str, str, Optional[str]]] = [
    ("Inter", "Inter", None),
    ("DM Sans", "DM Sans", None),
    ("Geist Sans", "Geist Sans", "Geist Mono"),
    ("Manrope", "Manrope", None),
]

HUMANIST_SERIF_BODY: List[Tuple[str, str, Optional[str]]] = [
    ("Fraunces", "Source Serif 4", None),
    ("Tiempos Headline", "Tiempos Text", None),
    ("Playfair Display", "Lora", None),
]

MONO_EVERYWHERE: List[Tuple[str, str, Optional[str]]] = [
    ("JetBrains Mono", "JetBrains Mono", "JetBrains Mono"),
    ("Geist Mono", "Geist Mono", "Geist Mono"),
    ("IBM Plex Mono", "IBM Plex Mono", "IBM Plex Mono"),
]

DISPLAY_MIXED: List[Tuple[str, str, Optional[str]]] = [
    ("Migra", "Inter", None),
    ("PP Editorial New", "Inter", None),
    ("Druk Wide", "Inter", None),
]


FONTS_BY_TYPOGRAPHY: Dict[str, List[Tuple[str, str, Optional[str]]]] = {
    "geometric-sans":      GEOMETRIC_SANS,
    "humanist-serif-body": HUMANIST_SERIF_BODY,
    "mono-everywhere":     MONO_EVERYWHERE,
    "display-mixed":       DISPLAY_MIXED,
}


# Variable-display: oversized headlines, often a variable-axis cut, body kept simple.
VARIABLE_DISPLAY: List[Tuple[str, str, Optional[str]]] = [
    ("Inter Display", "Inter", None),
    ("Recursive", "Inter", "Recursive Mono"),
    ("Geist Sans", "Geist Sans", "Geist Mono"),
    ("Inter Tight", "Inter", None),
]


FONTS_BY_TYPOGRAPHY["variable-display"] = VARIABLE_DISPLAY
