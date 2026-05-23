"""Invariants for every registered vertical."""
from __future__ import annotations

import pytest

from templates._brands import BRANDS_BY_VERTICAL
from templates.verticals import VERTICALS
from templates.verticals._base import VALID_ARCHETYPES


@pytest.mark.parametrize("name", sorted(VERTICALS))
def test_meta_basics(name):
    m = VERTICALS[name].META
    assert m.name == name, f"META.name {m.name!r} != module name {name!r}"
    assert m.archetype in VALID_ARCHETYPES
    assert m.difficulty in {"easy", "medium", "hard"}
    assert m.topic_description, f"{name}: empty topic_description"
    assert len(m.topic_description) >= 100, f"{name}: topic_description too short"
    assert m.sitemap_pool, f"{name}: empty sitemap_pool"
    assert m.sitemap_first in m.sitemap_pool
    assert 1 <= m.sitemap_min <= m.sitemap_max <= len(m.sitemap_pool)
    assert m.brand_verticals, f"{name}: no brand_verticals declared"


@pytest.mark.parametrize("name", sorted(VERTICALS))
def test_brand_verticals_resolve(name):
    """Every declared brand_vertical must be a key of BRANDS_BY_VERTICAL."""
    m = VERTICALS[name].META
    for bv in m.brand_verticals:
        assert bv in BRANDS_BY_VERTICAL, (
            f"{name}: brand_vertical {bv!r} not in BRANDS_BY_VERTICAL"
        )
        assert BRANDS_BY_VERTICAL[bv], (
            f"{name}: brand_vertical {bv!r} pool is empty"
        )


@pytest.mark.parametrize("name", sorted(VERTICALS))
def test_page_hints_subset_of_sitemap(name):
    """Every key in page_hints must be a page in the sitemap_pool."""
    m = VERTICALS[name].META
    for page in m.page_hints:
        assert page in m.sitemap_pool, (
            f"{name}: page_hints has {page!r} but it's not in sitemap_pool"
        )
