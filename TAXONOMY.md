# Synthesis taxonomy — what we sample to generate tasks

This is the design space for the Phase 2 synthesis pipeline. Each website
the pipeline produces is one point in (archetype × style × difficulty)
space. See GRADER.md for the grader; this doc covers the *generator*.

The taxonomy below was synthesised from a research pass (Lovable / v0 /
bolt / Linear / Stripe / Vercel / Awwwards / Design2Code) on 2026-05-21.

## 12 archetypes (page types)

Ordered by visual distinctiveness — sites in the same archetype look
roughly alike; sites across archetypes look very different.

| # | Archetype | What makes it visually distinct | Reference |
|---|---|---|---|
| A1 | Minimal SaaS landing | Wide hero, one-line value prop, single CTA, generous whitespace, subtle gradient | linear.app, attio.com |
| A2 | Feature-dense product page | Stacked feature blocks with screenshots, alternating L/R, mid-density copy | stripe.com/payments, vercel.com/products |
| A3 | Developer docs site | 3-pane layout (nav / content / TOC), mono in code blocks, no hero images | docs.stripe.com, biomejs.dev |
| A4 | Dashboard / app shell | Sidebar + topbar + data tables/charts, rounded cards, dense info | linear inbox, vercel dashboard |
| A5 | E-commerce PDP+PLP | Product grid, filter rail, large product photography, swatch pickers | gentlemonster.com, allbirds.com |
| A6 | Editorial / longform blog | Serif body, narrow measure (~65ch), pull quotes, drop caps, photographic lead | every.to, theverge features |
| A7 | Portfolio / agency | Big-typography hero, case-study tiles, motion-implied, opinionated grids | basicagency.com, locomotive.ca |
| A8 | Pricing-centric page | Tier comparison table, feature checkmarks, highlighted recommended tier | linear.app/pricing |
| A9 | Single-product splash / launch | One-page narrative, scroll-driven, oversized type, cinematic | rabbit.tech, humane.com |
| A10 | Community / forum / changelog | Threaded list, avatars, timestamps, lightweight cards | linear.app/changelog, lobste.rs |
| A11 | Restaurant / hospitality | Photographic hero, serif display, menu sections, location/hours | sweetgreen.com, ace hotels |
| A12 | Auth / onboarding flow | Centered card on bg-gradient, multi-step indicator, minimal chrome | clerk.dev, vercel/supabase login |

## 5 style axes (sample independently)

Crossing these with archetypes is what produces visually different
websites. Each axis has 5-6 concrete values.

| Axis | Values |
|---|---|
| **Density** | sparse / balanced / dense / editorial-narrow |
| **Color regime** | muted-editorial / brand-saturated / dark-native / pastel / glassy / neobrutalist-high-contrast |
| **Typography** | geometric-sans / humanist-serif-body / mono-everywhere / display-mixed / variable-display |
| **Border language** | flat / hairline-1px / soft-shadow-rounded / neobrutalist-thick / glassy-blurred |
| **Motif** | clean-iconographic / gradient-mesh / abstract-3d / photographic-product / illustration-heavy / data-viz-decor |

## Sitemap templates (5-7 pages each)

Every generated task has a multi-page sitemap matching its archetype.

| Archetype | Pages |
|---|---|
| A1 SaaS landing | home, features, pricing, customers, about, contact |
| A2 Product page | home, product-overview, how-it-works, use-cases, pricing, docs-link |
| A3 Docs | index, getting-started, guide-detail, api-reference, examples, changelog |
| A4 Dashboard | login, overview, detail-view, settings, billing, team |
| A5 E-com | home, collection, PDP, cart, about, journal |
| A6 Editorial | home, article-A, article-B, author-page, tag-page, about |
| A7 Portfolio | home, work-index, case-study-A, case-study-B, about, contact |
| A8 Pricing-led | home, pricing, compare, faq, customers, contact |
| A9 Splash | home, story, specs, preorder, faq, press |
| A10 Community | home, thread-index, thread-detail, user-profile, rules, changelog |
| A11 Restaurant | home, menu, reservations, about, location, press |
| A12 Auth | signup, login, verify, onboarding-step-1, onboarding-step-2, dashboard-empty |

## "AI tells" — what the generator must AVOID

These are the visual fingerprints that give away an LLM-generated site.
The synthesis pipeline's prompt to the LLM-compiler should explicitly
forbid them:

- Uniform vertical rhythm (`py-16` / `py-24` everywhere; no asymmetry)
- Single font family at 4 weights — no display/body contrast
- Snap-to-12-col grid; no broken/asymmetric layouts
- `rounded-xl shadow-sm` on every card regardless of brand
- Lucide icons + 3-stop linear gradient hero
- Centered headlines, never edge-aligned/oversized-display
- Always `bg-zinc-50` / `bg-white` with `text-zinc-900` body
- Hero → 3-feature-grid → testimonials → CTA (the "shadcn template")
- Pastel-on-white palette even when brand asks for editorial

The Lovable / v0 / bolt-saturated archetypes (A1, A8, A12) are valuable
to include precisely because top models nail them — they're the floor of
the score distribution, useful to compare against the harder archetypes.

## Cartesian sampling — exclusions and high-signal cells

Not every (archetype × style) combination is realistic.

**Nonsensical combinations to exclude:**

- `A3 docs × neobrutalist-thick` or `× abstract-3d` — docs need scannable hairlines
- `A4 dashboard × glassy-blurred` — kills data-table readability
- `A4 dashboard × humanist-serif-body` — numerals need tabular-mono
- `A6 editorial × mono-everywhere` — kills readability at length
- `A11 restaurant × dark-native + clean-iconographic` — kills appetite
- `A12 auth × dense` — auth is structurally sparse
- `A9 splash × dense + flat` — defeats cinematic purpose

**High-signal cells to guarantee coverage of** (these stress models AND
look meaningfully different):

| # | Cell | Reference style |
|---|---|---|
| 1 | A3 docs × mono-everywhere × hairline-1px | oxide.computer style |
| 2 | A6 editorial × humanist-serif-body × editorial-narrow × photographic | every.to style |
| 3 | A4 dashboard × dense × dark-native × data-viz-decor | linear / vercel dashboard |
| 4 | A7 portfolio × display-mixed × neobrutalist-thick | basicagency style |
| 5 | A11 restaurant × photographic-product × display-mixed × muted-editorial | ace-hotel style |
| 6 | A9 splash × abstract-3d × dark-native × variable-display | rabbit / humane style |
| 7 | A2 product × balanced × gradient-mesh × geometric-sans | stripe-style — saturated baseline as control |
| 8 | A5 ecom × pastel × hairline-1px × photographic-product | allbirds style |

## Initial 10-task slate

Cover both the AI-saturated archetypes (so we can see what easy looks
like) and the high-signal cells (so we can see what hard looks like):

| # | Archetype × style | Why included |
|---|---|---|
| 1 | A1 SaaS minimal × pastel × hairline-1px × clean-iconographic | Saturated control — every model should ace it |
| 2 | A8 pricing × dark-native × hairline-1px × clean-iconographic | Saturated control — pricing matrices are easy |
| 3 | A12 auth × pastel × glassy-blurred × clean-iconographic | Saturated control — sparse, modern, easy |
| 4 | A3 docs × mono-everywhere × hairline-1px × clean-iconographic | High-signal: typography + 3-pane layout |
| 5 | A6 editorial × humanist-serif × editorial-narrow × photographic | High-signal: typography + serif body + measure |
| 6 | A4 dashboard × dense × dark-native × data-viz-decor | High-signal: density + dark mode + tables |
| 7 | A7 portfolio × display-mixed × neobrutalist-thick × variable-display | High-signal: oversized type + asymmetry |
| 8 | A11 restaurant × photographic-product × display-mixed × muted-editorial | High-signal: hospitality aesthetic |
| 9 | A9 splash × abstract-3d × dark-native × variable-display | High-signal: cinematic single-product |
| 10 | A5 ecom × pastel × hairline-1px × photographic-product | High-signal: product grid + filtering |

This split (3 saturated + 7 hard) gives us a controlled difficulty
distribution: when we run Claude Code Opus 4.7 on these and grade,
we should see scores cluster in two bands — easy ~0.7-0.9, hard
~0.3-0.6 — with the spread being the actual signal.

## Schema (used by the pipeline)

```jsonc
WebsiteSpec {
  archetype:   "A1".."A12",
  vertical:    "saas|fintech|devtools|ecom-fashion|ecom-food|media|agency|hospitality|ai-product|b2b-ops",
  style: {
    density:         "sparse|balanced|dense|editorial-narrow",
    color_regime:    "muted-editorial|brand-saturated|dark-native|pastel|glassy|neobrutalist-high-contrast",
    typography:      "geometric-sans|humanist-serif-body|mono-everywhere|display-mixed|variable-display",
    border_language: "flat|hairline-1px|soft-shadow-rounded|neobrutalist-thick|glassy-blurred",
    motif:           "clean-iconographic|gradient-mesh|abstract-3d|photographic-product|illustration-heavy|data-viz-decor"
  },
  palette_seed:  "<hex>",
  font_pair:     ["<display>", "<body>", "<mono?>"],
  difficulty:    "easy|medium|hard",
  sitemap:       ["<page_archetype>", ...],   // 5-7 entries
  content_seed:  <int>,                       // for reproducible LLM prompts
  brand:         { name, tagline, value_prop, ... }
}
```

## Sources

- Glean research conversation (2026-05-21): visual scoring model design
- Recent UI-to-code work: Design2Code, WebSight, WebGen-Bench, UI2Code-N
- Lovable / v0 / bolt output observation
- Linear / Stripe / Vercel / Anthropic / Awwwards trends
