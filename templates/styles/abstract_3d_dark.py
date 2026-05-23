"""abstract_3d_dark — dark-native × variable-display × flat × abstract-3d.

rabbit.tech / humane.com / teenage.engineering visual language.
Cinematic single-product splash. Near-pure-black backgrounds, oversized
display headlines, the product image as hero.
"""
from templates import _fonts, _palettes
from templates.styles._base import StyleMeta

META = StyleMeta(
    name="abstract_3d_dark",
    color_regime="dark-native",
    typography="variable-display",
    border_language="flat",
    motif="abstract-3d",
    density_default="sparse",
    palette_pool=_palettes.DARK_NATIVE,
    font_pool=_fonts.VARIABLE_DISPLAY,
    style_notes=(
        "Background near-pure-black (#000 / #050505). The product is "
        "the show: oversized hero image, centered, ample negative space "
        "around it. Display headlines very large (120-200px) in a "
        "variable-axis cut. Body type small and spaced. Accent color "
        "appears as a single glow / underline / dot — never as filled "
        "card backgrounds. Sections alternate image-left / image-right. "
        "Avoid: shadcn-style card grids, multiple primary CTAs above "
        "the fold, sales-y discount language, light backgrounds."
    ),
    style_references=["rabbit.tech", "humane.com", "teenage.engineering"],
)
