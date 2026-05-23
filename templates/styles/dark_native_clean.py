"""dark_native_clean — dark-native × geometric-sans × hairline-1px × clean-iconographic.

The Vercel / Linear-dark / Stripe-dark visual language. Near-black
backgrounds, restrained accent, hairline 1px dividers, cards with
slightly lighter surfaces. Body weight slightly heavier (500) for
legibility on dark.
"""
from templates import _fonts, _palettes
from templates.styles._base import StyleMeta

META = StyleMeta(
    name="dark_native_clean",
    color_regime="dark-native",
    typography="geometric-sans",
    border_language="hairline-1px",
    motif="clean-iconographic",
    density_default="balanced",
    palette_pool=_palettes.DARK_NATIVE,
    font_pool=_fonts.GEOMETRIC_SANS,
    style_notes=(
        "Background near-black (#0A0A0B / #111114), text near-white "
        "(#F5F5F7) at high contrast, panel surface slightly lighter "
        "(#15151A). Single accent color from the palette used sparingly: "
        "highlighted CTA, hover state, active link. Body weight ~500 — "
        "slightly heavier than typical for legibility on dark. Hairline "
        "1px borders (#26262C) separate everything; no shadows, no "
        "rounded corners over 8px. Avoid: saturated gradients, default-"
        "Tailwind gray accents."
    ),
    style_references=["linear.app", "vercel.com", "stripe.com/dark"],
)
