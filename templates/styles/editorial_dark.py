"""editorial_dark — editorial-dark × humanist-serif-body × flat × photographic.

NYT magazine night-mode / longreads-dark / atavist-dark visual language.
Serif body on near-black, warm-amber accents. Cinematic photography.
The information-dense + reading-led counterpart to splash.
"""
from templates import _fonts, _palettes
from templates.styles._base import StyleMeta

META = StyleMeta(
    name="editorial_dark",
    color_regime="editorial-dark",
    typography="humanist-serif-body",
    border_language="flat",
    motif="photographic-product",
    density_default="balanced",
    palette_pool=_palettes.EDITORIAL_DARK,
    font_pool=_fonts.HUMANIST_SERIF_BODY,
    style_notes=(
        "Near-black background (#0E0D0B), warm-cream text (#F4EDE0 "
        "primary, #B5AB97 muted). Serif body type ~17-18px, "
        "line-height 1.55. Section headers in display serif at "
        "heavier weight. Hero photography full-bleed, treated with a "
        "dark gradient overlay so headline text reads white on top. "
        "Accent: warm amber / honey (palette anchor) for tag chips, "
        "links, byline accents. Pull quotes set in italic at oversized "
        "weight. NO sidebars; reading flow is top-down. NO sans-serif "
        "body, NO bright neon accents. The aesthetic is 'longform after "
        "midnight'."
    ),
    style_references=["nytimes.com night mode", "longreads.com", "theatavist.com"],
)
