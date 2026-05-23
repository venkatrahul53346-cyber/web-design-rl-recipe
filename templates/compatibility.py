"""Vertical × style compatibility matrix.

A positive list per vertical: which styles are visually plausible
for that topic. Easier to reason about than a "blacklist of bad
combinations" because the natural human question is "what styles fit
*this* vertical?", not "what's wrong with *this* combo?".

Adding a new vertical: define its set of compatible styles here.
Adding a new style: append it to the sets of verticals it fits.
"""
from __future__ import annotations

import random
from typing import List, Tuple


COMPATIBLE_STYLES: dict[str, set[str]] = {
    "saas_landing": {
        "saas_clean", "dark_native_clean", "mono_warm", "mono_dark",
        "glassy_pastel", "neobrut_thick",
    },
    "developer_docs": {
        "saas_clean", "dark_native_clean", "mono_warm", "mono_dark",
        "neobrut_thick",
    },
    "pricing_page": {
        "saas_clean", "dark_native_clean", "mono_dark", "glassy_pastel",
        "neobrut_thick",
    },
    "auth_flow": {
        "saas_clean", "dark_native_clean", "glassy_pastel", "crypto_neon",
    },
    "editorial_pub": {
        "serif_editorial", "photo_warm_display", "editorial_dark",
    },
    "dashboard_app": {
        "saas_clean", "dark_native_clean", "mono_warm", "mono_dark",
        "data_dense_dark",
    },
    "portfolio_studio": {
        "saas_clean", "dark_native_clean", "neobrut_thick",
        "serif_editorial", "photo_warm_display",
    },
    "ecom_storefront": {
        "saas_clean", "neobrut_thick", "photo_pastel", "photo_warm_display",
    },
    "product_splash": {
        "saas_clean", "dark_native_clean", "abstract_3d_dark",
        "photo_warm_display", "crypto_neon",
    },
    "restaurant": {
        "serif_editorial", "photo_warm_display",
    },
    "government": {
        "saas_clean", "dark_native_clean", "serif_editorial",
    },
    "hotel_booking": {
        "serif_editorial", "photo_warm_display",
    },
    "news_portal": {
        "serif_editorial", "editorial_dark",
    },
    "healthcare_clinic": {
        "saas_clean", "glassy_pastel",
    },
    "marketplace": {
        "saas_clean", "photo_pastel", "photo_warm_display",
    },
}


def is_compatible(vertical: str, style: str) -> bool:
    return style in COMPATIBLE_STYLES.get(vertical, set())


def list_compatible_styles(vertical: str) -> List[str]:
    return sorted(COMPATIBLE_STYLES.get(vertical, set()))


def all_valid_pairs() -> List[Tuple[str, str]]:
    """Every (vertical, style) pair the registry considers compatible."""
    return sorted(
        (v, s) for v, styles in COMPATIBLE_STYLES.items() for s in styles
    )


def random_compatible_pair(rng: random.Random) -> Tuple[str, str]:
    """Pick one (vertical, style) pair uniformly from the valid set.

    Note: uniform over PAIRS, not over verticals — verticals with more
    compatible styles are weighted higher. That's intentional: it
    matches the empirical truth that "saas_landing has more visual
    languages than restaurant" and we want to sample accordingly.
    """
    pairs = all_valid_pairs()
    return rng.choice(pairs)
