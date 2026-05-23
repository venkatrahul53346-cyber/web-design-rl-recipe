"""neobrut_thick — neobrutalist × variable-display × neobrutalist-thick × illustration-heavy.

basicagency.com / locomotive.ca visual language. Bold blocks, 2-3px
solid black borders, hard offset shadows, oversized display type.
"""
from templates import _fonts, _palettes
from templates.styles._base import StyleMeta

META = StyleMeta(
    name="neobrut_thick",
    color_regime="neobrutalist-high-contrast",
    typography="variable-display",
    border_language="neobrutalist-thick",
    motif="illustration-heavy",
    density_default="balanced",
    palette_pool=_palettes.NEOBRUTALIST_HIGH_CONTRAST,
    font_pool=_fonts.VARIABLE_DISPLAY,
    style_notes=(
        "Background single bold color from the palette OR pure off-white "
        "(#FAFAFA). Borders: solid 2-3px BLACK on every card / button / "
        "image frame. Drop shadows are BLACK and offset hard "
        "(translateX 4px, translateY 4px), no blur. Buttons translate-on-"
        "hover into their shadow. NO gradients, NO rounded corners over "
        "4px. Typography is the lead character: oversized display "
        "headlines (120-180px on desktop), variable-axis treatment if "
        "the font supports it, mixed weights and slants for visual "
        "rhythm. Body type small and tight (14-15px). Color is "
        "structural — bold blocks of yellow / red / blue used as section "
        "backgrounds. Avoid: corporate cleanness, even spacing on all "
        "sides, default Tailwind shadows."
    ),
    style_references=["basicagency.com", "locomotive.ca", "areweb.studio"],
)
