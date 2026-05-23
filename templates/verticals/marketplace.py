"""marketplace — multi-vendor marketplace storefront."""
from templates.verticals._base import VerticalMeta

META = VerticalMeta(
    name="marketplace",
    archetype="A5",
    difficulty="hard",
    topic_description=(
        "A multi-vendor marketplace — different from single-brand "
        "e-commerce in that the site is a host for many sellers. "
        "Pages emphasise discovery: filters, browse by category, "
        "browse by seller, reviews, ratings. Aesthetic is "
        "photography-led but with a wider variety of imagery (no "
        "single brand identity in product shots). Index is "
        "search/browse-led, NOT a single hero. PDP shows seller "
        "info prominently. Reviews + ratings live everywhere. "
        "Tone: neutral host, not partisan brand."
    ),
    page_hints={
        "index": "Search bar at top + browse-categories grid + "
                 "featured-sellers row + 'recently listed' product "
                 "grid + 'editor's picks' row. Multi-pattern, "
                 "discovery-led.",
        "category": "Category landing — masthead + filters (price, "
                    "rating, location, etc.) + product grid. Pagination "
                    "or infinite-scroll cue.",
        "PDP": "Large image left, product info right (name, "
               "price, rating + count, seller info, variant picker, "
               "primary CTA, longer description, reviews section "
               "below).",
        "seller-page": "Seller's storefront within the marketplace: "
                       "seller name, photo/logo, rating, intro, grid "
                       "of their products.",
        "reviews": "Filtered reviews list with photos, ratings, "
                   "dates, replies from seller. Could be standalone "
                   "or embedded in PDP.",
        "browse": "Multi-facet browse page — taxonomy tree + "
                  "filters + grid.",
        "sell": "Pitch page for prospective sellers: 'become a "
                "seller', benefits, requirements, sign-up CTA.",
    },
    sitemap_pool=["index", "category", "PDP", "seller-page",
                  "reviews", "browse", "sell"],
    sitemap_min=6, sitemap_max=7,
    brand_verticals=["marketplace"],
    references=["airbnb.com", "etsy.com", "reverb.com"],
)
