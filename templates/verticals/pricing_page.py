"""pricing_page (A8) — pricing-centric site (more depth than a generic landing)."""
from templates.verticals._base import VerticalMeta

META = VerticalMeta(
    name="pricing_page",
    archetype="A8",
    difficulty="easy",
    topic_description=(
        "A site centered on pricing — most often a product whose buying "
        "decision IS the pricing comparison (analytics tools, BI, "
        "infrastructure). The pricing page is the hero, not a "
        "secondary section. Three or four tier cards side-by-side, "
        "with one recommended highlighted. A separate compare page "
        "shows the full feature matrix. FAQ addresses the most-asked "
        "buying-decision questions. Used as a saturated control in "
        "the dataset because pricing matrices are easy structural "
        "shapes that every model nails."
    ),
    page_hints={
        "index": "Brand intro + 'see pricing' CTA. Short product summary, "
                 "tier preview (3 cards). Below: 1-2 trust-signal sections.",
        "pricing": "3-4 tier cards side-by-side, with one outlined or "
                   "marked 'Recommended'. Each: tier name, price (large), "
                   "1-line description, 6-10 feature bullets, primary CTA.",
        "compare": "Full feature-vs-tier matrix. Sticky header row, "
                   "hairline 1px row separators. Categories grouped.",
        "faq": "Collapsed accordion list, ~10 questions with concise "
               "answers. Buying-decision questions only.",
        "customers": "Logos + 1-2 testimonials. Short, no case studies "
                     "(this is a pricing-led page, not a marketing site).",
        "contact": "Sales contact (form + email + meeting-link CTA).",
        "enterprise": "Custom-pricing pitch: 'Talk to sales' CTA, "
                      "differentiators (security, SSO, contracts), 1 quote.",
    },
    sitemap_pool=["index", "pricing", "compare", "faq", "customers",
                  "contact", "enterprise"],
    sitemap_min=5, sitemap_max=6,
    brand_verticals=["saas", "devtools", "ai-product"],
    references=["linear.app/pricing", "vercel.com/pricing", "stripe.com/pricing"],
)
