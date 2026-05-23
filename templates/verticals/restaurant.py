"""restaurant (A11) — restaurant or hospitality venue site."""
from templates.verticals._base import VerticalMeta

META = VerticalMeta(
    name="restaurant",
    archetype="A11",
    difficulty="hard",
    topic_description=(
        "A site for a restaurant, café, or small hospitality venue. "
        "The aesthetic is photography-led, warm, considered. Index "
        "is full-bleed hero photograph + restaurant name + location/"
        "hours. Menu page lists dishes by section with prices. "
        "Reservations is a minimal form. About has chef/founder bio. "
        "Location has address + hours + map placeholder. Press shows "
        "media mentions. The tone is hospitable, not corporate. NO "
        "loyalty-program upsell, NO 'order online for delivery'."
    ),
    page_hints={
        "index": "Full-bleed hero photograph + restaurant name in "
                 "large display + dek (location + opening hours). "
                 "Below: short prose intro, glimpse of menu (3-4 "
                 "dishes with photos and prices), opening hours table.",
        "menu": "Sections (Starters / Mains / Drinks / Dessert), each "
                "a flat list — dish name (display weight), description "
                "(italic or smaller), price right-aligned with leader "
                "dots or whitespace.",
        "reservations": "Minimal form — date / time / party-size / "
                        "contact info / dietary notes textarea / submit.",
        "about": "Founder/chef bio + philosophy paragraph + "
                 "photographic interludes.",
        "location": "Address, embedded-map placeholder (a styled "
                    "rectangle), hours table by day of week, parking/"
                    "transit notes.",
        "press": "List of media mentions with publication name + "
                 "headline + date + outbound link.",
    },
    sitemap_pool=["index", "menu", "reservations", "about", "location", "press"],
    sitemap_min=6, sitemap_max=6,
    brand_verticals=["hospitality"],
    references=["acehotel.com restaurants", "lestrop.com", "sister-cities.com"],
)
