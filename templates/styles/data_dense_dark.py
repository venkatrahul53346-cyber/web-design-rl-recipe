"""data_dense_dark — dark-native × geometric-sans × hairline-1px × data-viz-decor.

Linear-dashboard / Vercel-dashboard / PlanetScale visual language. Dense
by default. KPI cards with sparklines, faint chart grids, hairline row
separators, tabular figures for numerals.
"""
from templates import _fonts, _palettes
from templates.styles._base import StyleMeta

META = StyleMeta(
    name="data_dense_dark",
    color_regime="dark-native",
    typography="geometric-sans",
    border_language="hairline-1px",
    motif="data-viz-decor",
    density_default="dense",
    palette_pool=_palettes.DARK_NATIVE,
    font_pool=_fonts.GEOMETRIC_SANS,
    style_notes=(
        "Background near-black (#0A0A0B), panel surface slightly lighter "
        "(#15151A), text on dark (#E5E5E7 primary, #8A8A92 muted). "
        "Persistent left sidebar (~220px) with nav groups. Persistent "
        "top bar with breadcrumbs + search + user menu. Hairline 1px "
        "borders (#26262C) separate everything; no shadows. KPI cards "
        "in 4-column grid (number large, label small, sparkline beneath). "
        "Wide chart with faint grid lines. Numerals MUST use tabular "
        "figures (`font-feature-settings: 'tnum'`). Charts as SVG or "
        "div-rendered. Avoid: rounded cards >8px radius, gradient "
        "decorations on data charts, oversized hero treatments."
    ),
    style_references=["linear.app", "vercel.com/dashboard", "planetscale.com"],
)
