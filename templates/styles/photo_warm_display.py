"""photo_warm_display — muted-editorial × display-mixed × flat × photographic-product.

The acehotel.com / sister-cities / lestrop visual language. Warm
neutral backgrounds, photography essential, display serif headlines,
clean sans body. Used for hospitality and other photography-led editorial.
"""
from templates import _fonts, _palettes
from templates.styles._base import StyleMeta

META = StyleMeta(
    name="photo_warm_display",
    color_regime="muted-editorial",
    typography="display-mixed",
    border_language="flat",
    motif="photographic-product",
    density_default="balanced",
    palette_pool=_palettes.MUTED_EDITORIAL,
    font_pool=_fonts.DISPLAY_MIXED,
    style_notes=(
        "Warm neutral background (#F4EFE7 / #FBF7F0). Photography is "
        "essential — full-bleed hero. Display headlines in a serif or "
        "display face (Migra / PP Editorial / Druk Wide), body in a "
        "clean sans for legibility. Soft, saturated accent (#7C2D12 "
        "rust or #854D0E ochre) used for links + primary CTA underline. "
        "Section breaks are flat — no borders, just whitespace. Avoid: "
        "SaaS-style feature cards, neon palettes, generic stock-photo "
        "placeholders."
    ),
    style_references=["acehotel.com", "lestrop.com", "sister-cities.com"],
)
