"""Hand-curated brand personas, partitioned by vertical.

Each entry is a believable startup identity: a real-feeling name + tagline
+ value prop + audience. The pool is intentionally finite (~10 in 2A,
expanded to ~50 in 2B) so seeded sampling is reproducible and we can
inspect the full set when debugging.

Templates declare which verticals they draw from via
``META.brand_verticals``; ``_base.sample_brand`` does the cross-vertical
filter so a restaurant brand never lands on a SaaS template.
"""
from __future__ import annotations

from typing import Dict, List

from templates._base import BrandPersona


_SAAS: List[BrandPersona] = [
    BrandPersona(
        name="Stellar",
        tagline="Software that thinks ahead",
        value_prop=(
            "A project-management platform built for the way modern engineering "
            "teams actually work — incidents, planning, and execution in one place."
        ),
        product_category="project management",
        target_audience="engineering teams at growth-stage startups",
        vertical="saas",
    ),
    BrandPersona(
        name="Lumen",
        tagline="Visibility into every workflow",
        value_prop=(
            "Lumen is a workflow analytics platform. It instruments the tools "
            "your team already uses — Jira, Slack, GitHub — and surfaces where "
            "work actually slows down."
        ),
        product_category="workflow analytics",
        target_audience="engineering managers and ops leads",
        vertical="saas",
    ),
    BrandPersona(
        name="Cobalt",
        tagline="The shared brain for product teams",
        value_prop=(
            "Cobalt connects research, specs, and decisions into one searchable "
            "space. Stop hunting through Notion, Linear, and Slack for the "
            "answer that already exists."
        ),
        product_category="knowledge management",
        target_audience="product managers and design leads",
        vertical="saas",
    ),
    BrandPersona(
        name="Northwind",
        tagline="Customer success without the spreadsheet",
        value_prop=(
            "Northwind unifies customer signals from your product, support "
            "tickets, and CRM so success teams know who needs attention before "
            "they churn."
        ),
        product_category="customer success",
        target_audience="customer success teams at B2B SaaS companies",
        vertical="saas",
    ),
    BrandPersona(
        name="Atlas",
        tagline="Headcount planning that keeps up",
        value_prop=(
            "Atlas turns hiring plans, comp bands, and org changes into a "
            "single source of truth shared between Finance and People."
        ),
        product_category="people ops",
        target_audience="People-ops and Finance partners at 100–1000 person companies",
        vertical="saas",
    ),
]


_DEVTOOLS: List[BrandPersona] = [
    BrandPersona(
        name="Tessera",
        tagline="Configuration as code, deployed in milliseconds",
        value_prop=(
            "Tessera is a feature-flag and dynamic-config platform for engineering "
            "teams. Define flags in code, evaluate them at the edge with sub-"
            "millisecond latency, and roll out or roll back with one command."
        ),
        product_category="feature flags / dynamic configuration",
        target_audience="senior engineers at companies running production services",
        vertical="devtools",
    ),
    BrandPersona(
        name="Riverbed",
        tagline="Observability that follows the request",
        value_prop=(
            "Riverbed traces every request across services without manual "
            "instrumentation. Open-source agent, hosted query plane, $0 to start."
        ),
        product_category="distributed tracing / observability",
        target_audience="platform and SRE teams",
        vertical="devtools",
    ),
    BrandPersona(
        name="Marrow",
        tagline="The debugger your build pipeline always wanted",
        value_prop=(
            "Marrow records every CI run as a replayable artifact: re-run any "
            "failing job locally with the exact environment, no Docker tricks."
        ),
        product_category="CI/CD tooling",
        target_audience="developer experience teams",
        vertical="devtools",
    ),
    BrandPersona(
        name="Glyph",
        tagline="API contracts that stay honest",
        value_prop=(
            "Glyph turns OpenAPI specs into typed clients, mocks, and contract "
            "tests in one command — keeping consumer and producer in sync as "
            "the API evolves."
        ),
        product_category="API tooling",
        target_audience="backend engineers and API platform teams",
        vertical="devtools",
    ),
    BrandPersona(
        name="Ferment",
        tagline="Reproducible builds, no Docker required",
        value_prop=(
            "Ferment hashes your build inputs and caches outputs across machines. "
            "Every developer gets the same artifact your CI does, in seconds."
        ),
        product_category="build tooling",
        target_audience="senior engineers at language-polyglot teams",
        vertical="devtools",
    ),
]


BRANDS_BY_VERTICAL: Dict[str, List[BrandPersona]] = {
    "saas":     _SAAS,
    "devtools": _DEVTOOLS,
}


_FINTECH = [
    BrandPersona(
        name="Reverb",
        tagline="Banking that moves at your speed",
        value_prop=(
            "Reverb is a fintech platform for high-growth companies — multi-currency "
            "accounts, virtual cards, programmatic spend controls, all in one API."
        ),
        product_category="business banking",
        target_audience="finance teams at series-B+ startups",
        vertical="fintech",
    ),
    BrandPersona(
        name="Tally",
        tagline="The credit card built for engineers",
        value_prop=(
            "Tally is a corporate card with a developer-first ledger: every "
            "transaction is queryable via SQL, exports stream into your data "
            "warehouse in real time."
        ),
        product_category="corporate cards",
        target_audience="finance + engineering at data-driven companies",
        vertical="fintech",
    ),
    BrandPersona(
        name="Mint Ledger",
        tagline="Close the books before lunch",
        value_prop=(
            "Mint Ledger automates AP, AR, and reconciliation for SMBs. Connect "
            "your bank and accounting software; the books update themselves."
        ),
        product_category="accounting automation",
        target_audience="founders and operators at small businesses",
        vertical="fintech",
    ),
]


_ECOM_FASHION = [
    BrandPersona(
        name="Half-Light",
        tagline="Quiet clothing, considered details",
        value_prop=(
            "Half-Light makes wardrobe staples in small batches from natural fibers "
            "and small mills. No seasonal collections, no markdowns — just clothes "
            "that earn a place in your closet."
        ),
        product_category="ready-to-wear",
        target_audience="design-literate adults",
        vertical="ecom-fashion",
    ),
    BrandPersona(
        name="Wren & Bell",
        tagline="Knitwear, in season again",
        value_prop=(
            "Wren & Bell knit in Naples on machines that haven't changed since "
            "the eighties. We make four pieces a year, in cashmere and merino."
        ),
        product_category="knitwear",
        target_audience="people who buy fewer, better things",
        vertical="ecom-fashion",
    ),
    BrandPersona(
        name="Argo",
        tagline="Footwear engineered for cities",
        value_prop=(
            "Argo makes one shoe in twelve colors. Vegetable-tanned, made in "
            "Portugal, designed for ten miles of pavement before lunch."
        ),
        product_category="footwear",
        target_audience="urban commuters who walk the city",
        vertical="ecom-fashion",
    ),
]


_MEDIA = [
    BrandPersona(
        name="The Marginal",
        tagline="The slow side of the news",
        value_prop=(
            "The Marginal is a longform publication about culture, economics, "
            "and what's next. Two pieces a week, never breaking news."
        ),
        product_category="independent magazine",
        target_audience="adults who pay for ideas",
        vertical="media",
    ),
    BrandPersona(
        name="Sandfork",
        tagline="Notes from the cooking class",
        value_prop=(
            "Sandfork is a cooking newsletter and journal — recipes, technique, "
            "and the people who make food. Published on paper twice a year."
        ),
        product_category="food publication",
        target_audience="serious home cooks",
        vertical="media",
    ),
]


_AGENCY = [
    BrandPersona(
        name="Mondrian Studio",
        tagline="Brand systems and digital products",
        value_prop=(
            "Mondrian is a small studio. We do brand identity, websites, and "
            "product design for ambitious teams. Five engagements a year."
        ),
        product_category="design studio",
        target_audience="founders shipping a flagship product",
        vertical="agency",
    ),
    BrandPersona(
        name="Locomotive",
        tagline="Motion-led design and engineering",
        value_prop=(
            "We build sites that move. Award-winning interactive experiences "
            "for brands with stories worth animating."
        ),
        product_category="creative studio",
        target_audience="brands with cinematic ambitions",
        vertical="agency",
    ),
]


_HOSPITALITY = [
    BrandPersona(
        name="Maison Vert",
        tagline="A small hotel in the old city",
        value_prop=(
            "Twelve rooms in a restored 18th-century townhouse. Slow breakfast, "
            "honest pasta, walking distance to everything that matters."
        ),
        product_category="boutique hotel",
        target_audience="design-conscious travelers",
        vertical="hospitality",
    ),
    BrandPersona(
        name="Salt & Field",
        tagline="A restaurant on a working farm",
        value_prop=(
            "Salt & Field is a forty-seat restaurant on a regenerative farm. "
            "Tasting menus only, served Thursday through Sunday."
        ),
        product_category="restaurant",
        target_audience="travelers and locals worth a drive",
        vertical="hospitality",
    ),
    BrandPersona(
        name="The Nettle Inn",
        tagline="A village pub with rooms",
        value_prop=(
            "Six rooms above a country pub. Fires lit by 4pm, tap list rotates "
            "weekly, dogs welcome anywhere except the dining room."
        ),
        product_category="inn / pub",
        target_audience="weekend visitors from the city",
        vertical="hospitality",
    ),
]


_AI_PRODUCT = [
    BrandPersona(
        name="Aether",
        tagline="The AI desk for knowledge work",
        value_prop=(
            "Aether is one place for every document, conversation, and decision "
            "you've made. Ask a question; get the answer with sources."
        ),
        product_category="AI knowledge assistant",
        target_audience="knowledge workers at growing companies",
        vertical="ai-product",
    ),
    BrandPersona(
        name="Pliny",
        tagline="An AI second pair of eyes for your code",
        value_prop=(
            "Pliny reviews every pull request the moment it opens — finds bugs, "
            "spots regressions, files concrete suggestions. Trained on your codebase."
        ),
        product_category="AI code review",
        target_audience="senior engineers and tech leads",
        vertical="ai-product",
    ),
    BrandPersona(
        name="Glimmer",
        tagline="The AI hardware for the next interface",
        value_prop=(
            "Glimmer is a wearable assistant — always-on, always-listening, "
            "always-yours. The screen-free interface for ambient computing."
        ),
        product_category="AI hardware / consumer device",
        target_audience="early adopters and creative professionals",
        vertical="ai-product",
    ),
]


BRANDS_BY_VERTICAL["fintech"]      = _FINTECH
BRANDS_BY_VERTICAL["ecom-fashion"] = _ECOM_FASHION
BRANDS_BY_VERTICAL["media"]        = _MEDIA
BRANDS_BY_VERTICAL["agency"]       = _AGENCY
BRANDS_BY_VERTICAL["hospitality"]  = _HOSPITALITY
BRANDS_BY_VERTICAL["ai-product"]   = _AI_PRODUCT
