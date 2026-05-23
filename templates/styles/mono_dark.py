"""mono_dark — dark-native × mono-everywhere × hairline-1px × clean-iconographic.

The warp.dev / ghostty / mostly-terminal-aesthetic devtool language.
Mono everywhere on dark surface — not just code blocks. Neon-green or
amber accent for terminal heritage. Designed for engineers.
"""
from templates import _fonts, _palettes
from templates.styles._base import StyleMeta

META = StyleMeta(
    name="mono_dark",
    color_regime="dark-native",
    typography="mono-everywhere",
    border_language="hairline-1px",
    motif="clean-iconographic",
    density_default="balanced",
    palette_pool=_palettes.DARK_NATIVE,
    font_pool=_fonts.MONO_EVERYWHERE,
    style_notes=(
        "Background near-pure-black (#0A0A0B / #0F0F11), text near-"
        "white (#E5E5E7) at high contrast. Mono typeface across ALL "
        "text — headings, body, code, captions. Hairline 1px borders "
        "(#222226), NO shadows, NO rounded corners > 4px. Accent "
        "color (palette anchor) used sparingly: terminal-green "
        "underline, amber inline-code highlight. Code blocks: subtle "
        "tinted-darker bg (#15151A), mono code with simulated syntax "
        "highlighting via colored spans. Designed for the terminal-"
        "comfortable engineer. Avoid: serif body, default Tailwind "
        "grays, bright gradients, rounded everything."
    ),
    style_references=["warp.dev", "ghostty.org", "fly.io/blog"],
)
