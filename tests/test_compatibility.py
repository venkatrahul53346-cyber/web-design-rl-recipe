"""sample_spec works for every compatible pair, raises for every incompatible pair."""
from __future__ import annotations

import pytest

from src.spec import WebsiteSpec
from templates import sample_spec
from templates.compatibility import COMPATIBLE_STYLES, all_valid_pairs
from templates.verticals import VERTICALS
from templates.styles import STYLES


SEEDS = (0, 1, 42, 99, 12345)


@pytest.mark.parametrize("v,s", all_valid_pairs())
@pytest.mark.parametrize("seed", SEEDS)
def test_valid_pair_samples_cleanly(v, s, seed):
    spec = sample_spec(v, s, seed)
    # roundtrip
    back = WebsiteSpec.from_json(spec.to_json())
    assert back.to_dict() == spec.to_dict()


@pytest.mark.parametrize("v,s", all_valid_pairs())
def test_archetype_matches_vertical(v, s):
    spec = sample_spec(v, s, seed=0)
    assert spec.archetype == VERTICALS[v].META.archetype


@pytest.mark.parametrize("v,s", all_valid_pairs())
def test_style_axes_match(v, s):
    spec = sample_spec(v, s, seed=0)
    sm = STYLES[s].META
    vm = VERTICALS[v].META
    assert spec.style.color_regime    == sm.color_regime
    assert spec.style.typography      == sm.typography
    assert spec.style.border_language == sm.border_language
    assert spec.style.motif           == sm.motif
    expected_density = vm.density_override or sm.density_default
    assert spec.style.density == expected_density


@pytest.mark.parametrize("v,s", all_valid_pairs())
def test_brand_within_allowed_verticals(v, s):
    spec = sample_spec(v, s, seed=0)
    assert spec.vertical in VERTICALS[v].META.brand_verticals


@pytest.mark.parametrize("v,s", all_valid_pairs())
def test_palette_and_font_from_pool(v, s):
    spec = sample_spec(v, s, seed=0)
    sm = STYLES[s].META
    assert spec.palette_seed in sm.palette_pool
    if sm.font_pair_locked:
        assert spec.font_pair == sm.font_pair_locked
    else:
        assert spec.font_pair in sm.font_pool


@pytest.mark.parametrize("v,s", all_valid_pairs())
def test_sitemap_within_bounds(v, s):
    spec = sample_spec(v, s, seed=0)
    vm = VERTICALS[v].META
    assert vm.sitemap_min <= len(spec.sitemap) <= vm.sitemap_max
    for page in spec.sitemap:
        assert page in vm.sitemap_pool


@pytest.mark.parametrize("v,s", all_valid_pairs())
def test_notes_interpolated(v, s):
    spec = sample_spec(v, s, seed=0)
    assert "{brand_name}" not in spec.notes
    assert "{references_csv}" not in spec.notes
    assert spec.brand.name in spec.notes


def test_invalid_pair_raises():
    # restaurant × crypto_neon is not in COMPATIBLE_STYLES
    with pytest.raises(ValueError, match="not in COMPATIBLE_STYLES"):
        sample_spec("restaurant", "crypto_neon", seed=0)


def test_unknown_vertical_raises():
    with pytest.raises(ValueError):
        sample_spec("nonexistent_vertical", "saas_clean", seed=0)


@pytest.mark.parametrize("v", sorted(VERTICALS))
def test_seed_determinism(v):
    """Same seed → identical spec on every call (no global mutable state)."""
    s = sorted(COMPATIBLE_STYLES[v])[0]
    a = sample_spec(v, s, seed=42)
    b = sample_spec(v, s, seed=42)
    assert a.to_dict() == b.to_dict()


@pytest.mark.parametrize("v", sorted(VERTICALS))
def test_seed_variance(v):
    """Different seeds → at least one of (brand, palette, font, sitemap) differs."""
    s = sorted(COMPATIBLE_STYLES[v])[0]
    a = sample_spec(v, s, seed=1)
    b = sample_spec(v, s, seed=99)
    differs = (
        a.brand.name != b.brand.name
        or a.palette_seed != b.palette_seed
        or a.font_pair != b.font_pair
        or a.sitemap != b.sitemap
    )
    assert differs, f"{v}/{s}: seeds 1 and 99 produced identical specs"
