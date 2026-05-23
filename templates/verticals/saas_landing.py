"""saas_landing (A1) — modern SaaS marketing site."""
from templates.verticals._base import VerticalMeta

META = VerticalMeta(
    name="saas_landing",
    archetype="A1",
    difficulty="easy",
    topic_description=(
        "A modern marketing site for a B2B SaaS product. The brand sells "
        "software-as-a-service to engineering or product teams. The site "
        "exists to convert visitors into trial users / leads, not to "
        "explain how to use the product. Hero is a clear single-line "
        "value proposition with one primary CTA (\"Start free\" / \"Book "
        "a demo\"). Below the fold, 2-4 distinct sections that "
        "demonstrate the product (NOT a generic 3-feature-grid). Use "
        "real product names, real customer quotes (made-up but "
        "plausible), real metrics. The tone is confident but not "
        "boastful. Avoid: lorem ipsum, \"feature one / feature two\" "
        "filler, the shadcn-template (hero → 3-feature-grid → "
        "testimonials → CTA)."
    ),
    page_hints={
        "index": "Hero with brand value prop + single primary CTA. Below: "
                 "2-4 differentiated sections (e.g. one product-screenshot "
                 "section, one comparison table, one testimonial quote, "
                 "one CTA strip). Avoid the shadcn template.",
        "features": "Deep dive: 4-6 feature blocks alternating L/R "
                    "(image / text), each focused on one capability with "
                    "concrete benefits.",
        "pricing": "Tier comparison. 2-4 plans side-by-side with feature "
                   "checkmarks. Highlight one recommended tier visually.",
        "customers": "Testimonial quotes, customer logos cluster, 1-2 "
                     "short case-study cards. Real-feeling names + titles "
                     "+ companies.",
        "about": "Mission paragraph, founding story, team grid (4-8 "
                 "placeholder people with roles), values list.",
        "contact": "Contact form (name, email, message), office "
                   "addresses (real-feeling cities), support links.",
        "integrations": "Logo grid of integrations + categories of what "
                        "they're for + 'request an integration' CTA.",
    },
    sitemap_pool=["index", "features", "pricing", "customers",
                  "about", "contact", "integrations"],
    sitemap_min=5, sitemap_max=6,
    brand_verticals=["saas", "devtools"],
    references=["linear.app", "attio.com"],
)
