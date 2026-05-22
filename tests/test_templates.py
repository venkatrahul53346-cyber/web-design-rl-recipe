"""Invariants every template must satisfy.

Catches META/sampler drift: a template's META declares what is locked
vs sampled; the sampler must produce specs consistent with that META,
or downstream prompt construction silently embeds wrong values.
"""
from __future__ import annotations

import json

import pytest

from src.spec import WebsiteSpec
from templates import REGISTRY


@pytest.mark.parametrize("name", sorted(REGISTRY))
@pytest.mark.parametrize("seed", [0, 1, 42, 99, 12345])
def test_sample_spec_roundtrip_json(name, seed):
    """sample_spec(seed) → JSON → sample_spec recovers identical spec."""
    spec = REGISTRY[name].sample_spec(seed)
    raw = spec.to_json()
    back = WebsiteSpec.from_json(raw)
    assert back.to_dict() == spec.to_dict()


@pytest.mark.parametrize("name", sorted(REGISTRY))
@pytest.mark.parametrize("seed", [0, 1, 42, 99, 12345])
def test_archetype_matches_meta(name, seed):
    spec = REGISTRY[name].sample_spec(seed)
    meta = REGISTRY[name].META
    assert spec.archetype == meta.archetype, (
        f"{name} sampler returned archetype {spec.archetype!r} but "
        f"META declares {meta.archetype!r}"
    )


@pytest.mark.parametrize("name", sorted(REGISTRY))
@pytest.mark.parametrize("seed", [0, 1, 42, 99, 12345])
def test_locked_style_axes_preserved(name, seed):
    """Every style axis declared as a string in META.style_axes must
    appear verbatim on the sampled StyleSpec."""
    spec = REGISTRY[name].sample_spec(seed)
    meta = REGISTRY[name].META
    for axis, value in meta.style_axes.items():
        if isinstance(value, str):
            assert getattr(spec.style, axis) == value, (
                f"{name} seed={seed}: style.{axis} = {getattr(spec.style, axis)!r} "
                f"but META locks it to {value!r}"
            )


@pytest.mark.parametrize("name", sorted(REGISTRY))
@pytest.mark.parametrize("seed", [0, 1, 42, 99, 12345])
def test_palette_and_font_from_pool(name, seed):
    spec = REGISTRY[name].sample_spec(seed)
    meta = REGISTRY[name].META
    assert spec.palette_seed in meta.palette_pool, (
        f"{name} seed={seed}: palette {spec.palette_seed!r} not in declared pool"
    )
    if meta.font_pair_locked is not None:
        assert spec.font_pair == meta.font_pair_locked
    else:
        assert spec.font_pair in meta.font_pool, (
            f"{name} seed={seed}: font {spec.font_pair!r} not in declared pool"
        )


@pytest.mark.parametrize("name", sorted(REGISTRY))
@pytest.mark.parametrize("seed", [0, 1, 42, 99, 12345])
def test_sitemap_within_bounds(name, seed):
    spec = REGISTRY[name].sample_spec(seed)
    meta = REGISTRY[name].META
    assert meta.sitemap_min <= len(spec.sitemap) <= meta.sitemap_max
    for page in spec.sitemap:
        assert page in meta.sitemap_pool, (
            f"{name} seed={seed}: page {page!r} not in declared sitemap_pool"
        )


@pytest.mark.parametrize("name", sorted(REGISTRY))
@pytest.mark.parametrize("seed", [0, 1, 42, 99, 12345])
def test_brand_vertical_allowed(name, seed):
    spec = REGISTRY[name].sample_spec(seed)
    meta = REGISTRY[name].META
    assert spec.vertical in meta.brand_verticals, (
        f"{name} seed={seed}: brand vertical {spec.vertical!r} not in "
        f"META.brand_verticals={meta.brand_verticals}"
    )


@pytest.mark.parametrize("name", sorted(REGISTRY))
def test_seed_determinism(name):
    """Same seed → identical spec across two calls (no mutable global state)."""
    a = REGISTRY[name].sample_spec(seed=42)
    b = REGISTRY[name].sample_spec(seed=42)
    assert a.to_dict() == b.to_dict()


@pytest.mark.parametrize("name", sorted(REGISTRY))
def test_seed_variance(name):
    """Different seeds → at least *something* differs (brand or palette).

    Doesn't have to be all of them every time; just guards against a
    sampler that ignores the seed entirely.
    """
    a = REGISTRY[name].sample_spec(seed=1)
    b = REGISTRY[name].sample_spec(seed=99)
    differs = (a.brand.name != b.brand.name) or (a.palette_seed != b.palette_seed) \
              or (a.font_pair != b.font_pair) or (a.sitemap != b.sitemap)
    assert differs, f"{name}: seeds 1 and 99 produced identical specs"


@pytest.mark.parametrize("name", sorted(REGISTRY))
def test_design_notes_interpolated(name):
    """Notes should not contain raw `{brand_name}` / `{references_csv}`
    placeholders — format_notes must run."""
    spec = REGISTRY[name].sample_spec(seed=42)
    assert "{brand_name}" not in spec.notes
    assert "{brand_tagline}" not in spec.notes
    assert "{references_csv}" not in spec.notes
    # And the brand name should actually appear (sanity that interpolation hit).
    assert spec.brand.name in spec.notes
