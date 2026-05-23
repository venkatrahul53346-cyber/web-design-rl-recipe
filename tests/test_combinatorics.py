"""Sanity invariants on the matrix as a whole."""
from __future__ import annotations

from templates.compatibility import COMPATIBLE_STYLES, all_valid_pairs
from templates.verticals import VERTICALS
from templates.styles import STYLES


def test_every_vertical_has_at_least_one_style():
    for v in VERTICALS:
        assert v in COMPATIBLE_STYLES, f"{v} missing from COMPATIBLE_STYLES"
        assert COMPATIBLE_STYLES[v], f"{v}: no compatible styles"


def test_every_style_used_at_least_once():
    referenced = {s for styles in COMPATIBLE_STYLES.values() for s in styles}
    for s in STYLES:
        assert s in referenced, f"{s} is registered but no vertical uses it"


def test_total_pairs_at_least_50():
    """We want a wide enough matrix that the dataset isn't accidentally narrow."""
    pairs = all_valid_pairs()
    assert len(pairs) >= 50, f"only {len(pairs)} valid pairs"


def test_no_dangling_styles_in_matrix():
    """Every style referenced in COMPATIBLE_STYLES must be in STYLES."""
    referenced = {s for styles in COMPATIBLE_STYLES.values() for s in styles}
    missing = referenced - set(STYLES)
    assert not missing, f"COMPATIBLE_STYLES references unknown styles: {missing}"


def test_no_dangling_verticals_in_matrix():
    """Every vertical key in COMPATIBLE_STYLES must be in VERTICALS."""
    missing = set(COMPATIBLE_STYLES) - set(VERTICALS)
    assert not missing, f"COMPATIBLE_STYLES has unknown verticals: {missing}"
