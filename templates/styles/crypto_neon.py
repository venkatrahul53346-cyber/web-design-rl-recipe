"""crypto_neon — neon × geometric-sans × hairline-1px × abstract-3d.

The uniswap.com / ledger.com / magiceden.io visual language. Near-black
backgrounds with high-saturation neon accents (cyan, magenta, lime).
Data-heavy, animated-feel charts, "connect wallet" buttons, abstract
3D motifs.
"""
from templates import _fonts, _palettes
from templates.styles._base import StyleMeta

META = StyleMeta(
    name="crypto_neon",
    color_regime="neon",
    typography="geometric-sans",
    border_language="hairline-1px",
    motif="abstract-3d",
    density_default="balanced",
    palette_pool=_palettes.NEON,
    font_pool=_fonts.GEOMETRIC_SANS,
    style_notes=(
        "Background near-pure-black (#000 / #08080C). High-saturation "
        "neon accent (palette anchor) used for primary CTAs, glowing "
        "data points, animated decorations. Hairline 1px borders "
        "(#1A1A22) for cards. Display headlines large with optional "
        "neon glow (text-shadow). Body type clean sans at high "
        "contrast (#F0F0F8). Decorative motif: abstract 3D blobs / "
        "iridescent gradients in palette colors. CTA buttons "
        "neon-filled. \"Connect wallet\" or similar action button "
        "prominent. Numerals tabular for chart data. Avoid: warm "
        "muted palettes, serif body, default-Tailwind dark-mode "
        "(this is louder)."
    ),
    style_references=["uniswap.org", "ledger.com", "magiceden.io"],
)
