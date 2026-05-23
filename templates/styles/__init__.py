"""STYLES registry — explicit dict of style_name → module."""
from __future__ import annotations

from typing import Dict

from templates.styles import (
    abstract_3d_dark,
    crypto_neon,
    dark_native_clean,
    data_dense_dark,
    editorial_dark,
    glassy_pastel,
    mono_dark,
    mono_warm,
    neobrut_thick,
    photo_pastel,
    photo_warm_display,
    saas_clean,
    serif_editorial,
)


STYLES: Dict[str, object] = {
    "saas_clean":         saas_clean,
    "dark_native_clean":  dark_native_clean,
    "glassy_pastel":      glassy_pastel,
    "mono_warm":          mono_warm,
    "mono_dark":          mono_dark,
    "serif_editorial":    serif_editorial,
    "editorial_dark":     editorial_dark,
    "data_dense_dark":    data_dense_dark,
    "neobrut_thick":      neobrut_thick,
    "photo_pastel":       photo_pastel,
    "photo_warm_display": photo_warm_display,
    "abstract_3d_dark":   abstract_3d_dark,
    "crypto_neon":        crypto_neon,
}
