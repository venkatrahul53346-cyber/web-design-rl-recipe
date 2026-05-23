"""photo_pastel — pastel × geometric-sans × hairline-1px × photographic-product.

The allbirds.com / everlane.com / muji.com visual language. Pale
warm-neutral backgrounds, photography is the lead, hairline 1px
dividers, no shadows.
"""
from templates import _fonts, _palettes
from templates.styles._base import StyleMeta

META = StyleMeta(
    name="photo_pastel",
    color_regime="pastel",
    typography="geometric-sans",
    border_language="hairline-1px",
    motif="photographic-product",
    density_default="balanced",
    palette_pool=_palettes.PASTEL_PURPLES_AND_BLUES,
    font_pool=_fonts.GEOMETRIC_SANS,
    style_notes=(
        "Pale, warm-neutral background (#FAF8F5 / #F7F5F0). Photography "
        "is the lead — full-bleed hero image and large product photos. "
        "Hairline 1px dividers, no shadows. Quiet, considered, no "
        "discount-driven urgency. Filter rails on collection pages with "
        "hairline-divided checkbox lists. Product tiles: image, name, "
        "price, optional swatch row. Avoid: carousel arrows, bright "
        "sale banners, shadowed cards (defeats hairline-1px), Comic-"
        "Sans-style informal typography."
    ),
    style_references=["allbirds.com", "everlane.com", "muji.com"],
)
