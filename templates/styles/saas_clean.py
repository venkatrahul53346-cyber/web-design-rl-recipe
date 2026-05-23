"""saas_clean — pastel × geometric-sans × hairline-1px × clean-iconographic.

The Linear / Attio / Stripe consumer-product visual language. Sparse,
generous whitespace, single accent color, 1px borders only, off-white
backgrounds.
"""
from templates import _fonts, _palettes
from templates.styles._base import StyleMeta

META = StyleMeta(
    name="saas_clean",
    color_regime="pastel",
    typography="geometric-sans",
    border_language="hairline-1px",
    motif="clean-iconographic",
    density_default="sparse",
    palette_pool=_palettes.PASTEL_PURPLES_AND_BLUES,
    font_pool=_fonts.GEOMETRIC_SANS,
    style_notes=(
        "Lots of whitespace, 1px borders on cards (no shadows), single "
        "accent color from the palette, pale off-white backgrounds. "
        "Avoid centered-on-everything; use generous left-aligned hero "
        "typography. Hero takes ~70vh on first paint. Buttons are pill-"
        "shaped or sharp 6-8px radius. Cards are flat, separated by "
        "hairline borders. NO drop shadows, NO heavy gradients."
    ),
    style_references=["linear.app", "attio.com", "stripe.com"],
)
