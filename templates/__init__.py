"""Template registry — explicit, no autoglob.

Each generation run picks a template (either via ``--template <name>`` or
``--random-template``) and calls ``REGISTRY[name].sample_spec(seed)``.
Modules with a leading underscore (``_base``, ``_brands``,
``_palettes``, ``_fonts``) are infrastructure and are deliberately
NOT registered.

To add a new template:
1. Create ``templates/my_template.py`` with ``META``, ``DESIGN_NOTES``,
   and ``sample_spec(seed)``.
2. Import it here and add it to ``REGISTRY``.
3. Add a roundtrip case in ``tests/test_templates.py``.
"""
from __future__ import annotations

from typing import Dict

from templates import (
    auth_glassy,
    dashboard_dense,
    docs_mono,
    ecom_pastel,
    editorial_serif,
    portfolio_neobrut,
    pricing_dark,
    restaurant_photo,
    saas_minimal,
    splash_3d,
)


REGISTRY: Dict[str, object] = {
    "saas_minimal":      saas_minimal,
    "docs_mono":         docs_mono,
    "pricing_dark":      pricing_dark,
    "auth_glassy":       auth_glassy,
    "editorial_serif":   editorial_serif,
    "dashboard_dense":   dashboard_dense,
    "portfolio_neobrut": portfolio_neobrut,
    "ecom_pastel":       ecom_pastel,
    "splash_3d":         splash_3d,
    "restaurant_photo":  restaurant_photo,
}
