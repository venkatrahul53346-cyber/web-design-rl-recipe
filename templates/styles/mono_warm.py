"""mono_warm — muted-editorial × mono-everywhere × hairline-1px × clean-iconographic.

The oxide.computer / biomejs.dev / rauno.me visual language. Mono
typography across ALL text — headings, body, code, captions. Warm
off-white backgrounds, dark ink text, single deep accent.
"""
from templates import _fonts, _palettes
from templates.styles._base import StyleMeta

META = StyleMeta(
    name="mono_warm",
    color_regime="muted-editorial",
    typography="mono-everywhere",
    border_language="hairline-1px",
    motif="clean-iconographic",
    density_default="balanced",
    palette_pool=_palettes.MUTED_EDITORIAL,
    font_pool=_fonts.MONO_EVERYWHERE,
    style_notes=(
        "Mono typeface across ALL text — headings, body, code, captions. "
        "Hairline 1px borders, NO box-shadows, NO rounded corners (or "
        "0–2px max). Background: warm off-white (#FBF8F3), text: dark "
        "ink (#1A1815). Accent (palette anchor) used sparingly for the "
        "logomark, active link state, and inline-code highlight. Code "
        "blocks must be visually distinct: slightly tinted background "
        "(#F2EFE7), 1px border on top+bottom, simulated syntax "
        "highlighting via colored spans (keywords #6E5BCB, strings "
        "#007E5A, comments #888)."
    ),
    style_references=["oxide.computer/docs", "biomejs.dev", "rauno.me"],
)
