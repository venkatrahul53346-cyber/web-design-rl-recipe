"""product_splash (A9) — single-product cinematic launch page."""
from templates.verticals._base import VerticalMeta

META = VerticalMeta(
    name="product_splash",
    archetype="A9",
    difficulty="hard",
    topic_description=(
        "A cinematic single-product splash page — usually for an AI "
        "hardware device or a flagship consumer product launch. The "
        "page IS the product. Index is hero + scroll-driven feature "
        "beats (each section = one image + one short copy block). "
        "Story page is long-form narrative. Specs page is a "
        "specification table. Preorder is minimal (email + country). "
        "FAQ is a vertical accordion. Press has logos + media "
        "mentions. Avoid feature-grid cards; this is intentionally "
        "low-density."
    ),
    page_hints={
        "index": "Hero is product image + 1-2 line tagline, NO CTA "
                 "above the fold (the page itself is the CTA). Below: "
                 "scroll-revealed feature beats — each section a "
                 "single image + short copy, alternating image-left / "
                 "image-right.",
        "story": "Long-form narrative about the product. Oversized "
                 "type, photographic interludes. Reads like an essay.",
        "specs": "Technical spec table — dimensions, weight, battery, "
                 "materials. Tabular figures, hairline dividers, no "
                 "decorations.",
        "preorder": "Minimal form — email + (optional) shipping country, "
                    "oversized CTA, FAQ link.",
        "faq": "Vertical accordion. ~10 questions, concise answers.",
        "press": "Press logos cluster + recent media mentions list + "
                 "press contact.",
    },
    sitemap_pool=["index", "story", "specs", "preorder", "faq", "press"],
    sitemap_min=6, sitemap_max=6,
    brand_verticals=["ai-product"],
    references=["rabbit.tech", "humane.com", "teenage.engineering"],
)
