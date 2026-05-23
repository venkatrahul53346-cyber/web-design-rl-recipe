"""developer_docs (A3) — technical documentation site for a developer tool."""
from templates.verticals._base import VerticalMeta

META = VerticalMeta(
    name="developer_docs",
    archetype="A3",
    difficulty="hard",
    topic_description=(
        "Technical documentation for a developer-facing product. The "
        "site is read by engineers integrating the product into their "
        "stack. It exists to teach, not to sell. The shape is 3-pane "
        "on detail pages: left rail navigation tree, center prose+code "
        "(~720px max measure), right rail page TOC. Index page may be "
        "2-pane or single-column. Code is the lead: every page should "
        "have at least one code block. Code blocks are visually "
        "distinct (tinted background, simulated syntax highlighting via "
        "colored spans). Each page has content appropriate to its "
        "purpose — install commands on getting-started, parameter "
        "tables on api-reference, step-by-step recipes on guides, full "
        "snippets on examples. AVOID generic 'feature one / feature "
        "two' filler — this is technical content."
    ),
    page_hints={
        "index": "Docs landing — short overview of what the product is, "
                 "links to getting-started and key sections. May be "
                 "2-pane (left nav + content) or single-column.",
        "getting-started": "Quickstart guide. Install command in a code "
                           "block, minimal hello-world example, then "
                           "next-steps links. 3-pane layout.",
        "api-reference": "API endpoint or function reference. 2-3 "
                         "endpoints with: signature, parameter table, "
                         "request example (code block), response example.",
        "guides": "List of cookbook recipes. 4-6 guide cards with title "
                  "+ 1-line description, leading to detailed steps.",
        "examples": "Code-heavy. 3-5 self-contained integration "
                    "snippets in different languages or for different "
                    "use-cases. Each snippet ~10-30 lines in a code block.",
        "changelog": "Reverse-chronological list. Each entry: version "
                     "number + date + bullet-point changes. 5-8 entries.",
    },
    sitemap_pool=["index", "getting-started", "api-reference",
                  "guides", "examples", "changelog"],
    sitemap_min=6, sitemap_max=6,
    brand_verticals=["devtools"],
    references=["oxide.computer/docs", "biomejs.dev", "supabase.com/docs"],
)
