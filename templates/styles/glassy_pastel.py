"""glassy_pastel — pastel × geometric-sans × glassy-blurred × clean-iconographic.

Frosted-glass cards on soft gradient fields. Clerk / Vercel-login /
Supabase-signup visual language. Sparse by structure.
"""
from templates import _fonts, _palettes
from templates.styles._base import StyleMeta

META = StyleMeta(
    name="glassy_pastel",
    color_regime="glassy",
    typography="geometric-sans",
    border_language="glassy-blurred",
    motif="clean-iconographic",
    density_default="sparse",
    palette_pool=_palettes.PASTEL_PURPLES_AND_BLUES + _palettes.GLASSY,
    font_pool=_fonts.GEOMETRIC_SANS,
    style_notes=(
        "Backgrounds are soft gradient fields (palette anchor at 8-12% "
        "saturation, blending to a light neutral). Content lives in "
        "centered cards (~420px wide for forms) with a frosted-glass "
        "effect: subtle backdrop-filter blur, semi-transparent white "
        "background (rgba(255,255,255,0.7)), 1px translucent border. "
        "Buttons primary-filled with the palette anchor. Avoid: heavy "
        "shadows, busy backgrounds, opaque white cards (defeats glassy)."
    ),
    style_references=["clerk.dev", "vercel.com/login", "supabase.com/dashboard/sign-in"],
)
