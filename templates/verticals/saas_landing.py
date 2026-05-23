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

    # ---- Pattern axes (drive within-pair visual variance) ----
    hero_patterns=[
        # Linear.app — big centered headline, no product shot above the fold.
        "centered-text-only: a single short headline (3-7 words) and one sub-line "
        "centered horizontally and vertically in the hero. NO product screenshot, "
        "NO illustration. Two CTAs side-by-side under the sub-line. The fold "
        "feels intentionally empty.",
        # Attio.com — split, screenshot dominant.
        "text-left-product-shot-right: split hero, ~45% text on the left "
        "(headline + sub-line + CTA), ~55% on the right showing a stylised "
        "product screenshot or app-window mockup with subtle drop shadow.",
        # Vercel.com — text first, screenshot below the fold.
        "text-center-product-shot-below: centered text block (headline, sub-line, "
        "two CTAs) at the top, then a wide product-screenshot mockup spanning "
        "~80% of the viewport BELOW the text — not in the fold itself.",
        # Retool.com — abstract illustration replaces screenshot.
        "text-left-illustration-right: split hero, text on the left, but the "
        "right side is an ABSTRACT vector illustration (geometric shapes, "
        "soft gradients, no UI screenshot) — feels designerly rather than "
        "product-demonstrative.",
        # Basicagency.com — text and image asymmetric.
        "asymmetric-stagger: deliberately off-grid hero. Headline broken across "
        "two lines with the second line indented or offset. CTA below at an "
        "unexpected horizontal position. Optional small image element placed "
        "asymmetrically (top-right corner, NOT a balanced split).",
        # Tldraw.com — interactive widget instead of screenshot.
        "hero-with-inline-demo: text on top, then INSIDE the hero an interactive-"
        "looking widget (a styled card showing what the product does — a fake "
        "code block, a fake form, a fake chat bubble — visually integrated, "
        "not a screenshot).",
    ],
    nav_patterns=[
        # The default — present in ~80% of generated sites currently.
        "topbar-horizontal-links: standard top bar, brand wordmark on the left, "
        "4-6 horizontal text links centered or right-aligned, primary CTA "
        "button on the far right.",
        # Stripe — hover reveals 5-col mega menu.
        "topbar-with-mega-dropdown: top bar identical to horizontal-links but "
        "indicate (visually with a chevron + a hint) that 1-2 of the links "
        "would expand into a wide mega-dropdown menu with categorised links. "
        "Style the dropdown indicator clearly.",
        # Vercel marketing 2024 — rounded floating bar mid-page.
        "floating-pill-nav: the entire nav is a rounded pill / capsule floating "
        "with margin from the viewport edges, with a soft shadow. Brand on "
        "left, links centered, CTA on right. Visually it 'floats' rather than "
        "spanning edge-to-edge.",
        # Linear — minimal nav, ⌘K is the discovery affordance.
        "minimal-with-cmd-k: ultra-minimal nav. Just the brand wordmark on the "
        "left, plus a single CTA button on the right. ALSO render a ⌘K search "
        "pill in the center of the nav (styled like a search field with a kbd "
        "shortcut hint).",
        # GitHub — top utility bar + below it the product nav.
        "dual-bar: TWO horizontal bars stacked. The top thin bar has utility "
        "links (status, changelog, login) right-aligned. Below it, the main "
        "nav with brand left, primary navigation centered, primary CTA right.",
    ],
    section_arcs=[
        # The shadcn-template default. Currently used by ~60% of generations.
        # Listed so the others have something to contrast against.
        "hero -> three-feature-grid -> testimonial-strip -> pricing-tier -> cta-bottom",
        # Stripe-style — proof-heavy.
        "hero -> social-proof-logos -> benefits-paragraph -> demo-video-placeholder -> cta-bottom",
        # Comparison-led — ChatGPT-Pro style.
        "hero -> comparison-table -> faq -> pricing-tier -> cta-bottom",
        # Integration-grid led.
        "hero -> integration-grid -> use-case-cards -> numbers-stats-strip -> cta-bottom",
        # Walkthrough-led — for products with novel UX.
        "hero -> step-by-step-walkthrough -> benefits-paragraph -> testimonial-strip -> pricing-tier",
        # Case-study-led — for enterprise / agency-flavoured SaaS.
        "hero -> case-study-spotlight -> features-block -> testimonial-strip -> cta-bottom",
    ],
    density_modifiers=[
        "airy: 96px section padding, 1.65 line-height, generous whitespace "
        "between elements. Let sections breathe. The page should feel "
        "intentionally spacious.",
        "tight: 56px section padding, 1.45 line-height, condensed gaps. "
        "Information density per fold is high but not crowded.",
        "mixed-rhythm: alternate section padding between airy (96px) and "
        "tight (56px) for visual rhythm — every other section has different "
        "vertical breathing room.",
    ],
)
