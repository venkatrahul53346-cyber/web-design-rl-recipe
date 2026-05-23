"""serif_editorial — muted-editorial × humanist-serif × flat × photographic.

every.to / theverge.com/features / harpers.org visual language. Serif
body at ~18-19px, line-height 1.6, narrow measure (~65ch).
"""
from templates import _fonts, _palettes
from templates.styles._base import StyleMeta

META = StyleMeta(
    name="serif_editorial",
    color_regime="muted-editorial",
    typography="humanist-serif-body",
    border_language="flat",
    motif="photographic-product",
    density_default="editorial-narrow",
    palette_pool=_palettes.MUTED_EDITORIAL,
    font_pool=_fonts.HUMANIST_SERIF_BODY,
    style_notes=(
        "Serif body type at 18-19px, line-height 1.6, measure ~65ch "
        "(~640-680px). Body in a humanist serif (Tiempos, Source Serif, "
        "Lora). Display headlines in the same family at heavier weight "
        "OR a paired display serif. Generous vertical rhythm. Background "
        "warm off-white (#FBF8F3 or pure #FFF), text dark ink (#1A1815). "
        "Accent only for links + tag chips. NO sidebars during article "
        "body — keep the measure narrow. NO sans-serif body, NO "
        "centered text blocks, NO cards with shadows."
    ),
    style_references=["every.to", "theverge.com/features", "harpers.org"],
)
