"""Invariants for every registered style."""
from __future__ import annotations

import pytest

from templates.styles import STYLES
from templates.styles._base import (
    VALID_BORDERS, VALID_COLOR_REGIMES, VALID_DENSITIES,
    VALID_MOTIFS, VALID_TYPOGRAPHIES,
)


@pytest.mark.parametrize("name", sorted(STYLES))
def test_meta_axes(name):
    m = STYLES[name].META
    assert m.name == name
    assert m.color_regime in VALID_COLOR_REGIMES
    assert m.typography in VALID_TYPOGRAPHIES
    assert m.border_language in VALID_BORDERS
    assert m.motif in VALID_MOTIFS
    assert m.density_default in VALID_DENSITIES


@pytest.mark.parametrize("name", sorted(STYLES))
def test_pools_non_empty(name):
    m = STYLES[name].META
    assert m.palette_pool, f"{name}: empty palette_pool"
    if m.font_pair_locked is None:
        assert m.font_pool, f"{name}: empty font_pool and no lock"


@pytest.mark.parametrize("name", sorted(STYLES))
def test_palette_hex_format(name):
    m = STYLES[name].META
    for hex_val in m.palette_pool:
        assert hex_val.startswith("#") and len(hex_val) == 7, (
            f"{name}: bad hex {hex_val!r}"
        )


@pytest.mark.parametrize("name", sorted(STYLES))
def test_style_notes_present(name):
    m = STYLES[name].META
    assert m.style_notes and len(m.style_notes) >= 50
    assert m.style_references, f"{name}: no style_references"
