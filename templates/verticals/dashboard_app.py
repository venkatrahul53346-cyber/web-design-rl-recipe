"""dashboard_app (A4) — internal-product application shell with data tables."""
from templates.verticals._base import VerticalMeta

META = VerticalMeta(
    name="dashboard_app",
    archetype="A4",
    difficulty="hard",
    topic_description=(
        "An internal product / SaaS application shell. NOT a marketing "
        "page — this is what users see after they log in. Persistent "
        "left sidebar (~220px) with nav groups. Persistent top bar "
        "with breadcrumbs + search + user menu. Pages are dense: KPI "
        "cards, data tables with sortable columns, charts, recent-"
        "activity feeds. Numerals MUST use tabular figures. The "
        "aesthetic is calm-enterprise, NOT Bloomberg-terminal — "
        "restrained accent only, no rainbow charts."
    ),
    page_hints={
        "overview": "KPI cards in a 4-column grid (number large, label "
                    "small, sparkline beneath), then a wide chart, then "
                    "recent-activity feed and a data table.",
        "detail-view": "Header with breadcrumbs, filter row, dense data "
                       "table with sortable columns and hairline rows. "
                       "Sidebar visible.",
        "settings": "Left rail of settings categories, right pane with "
                    "the active form. Standard form patterns.",
        "billing": "Current plan card, invoice table with status pills, "
                   "payment-method tile, usage chart.",
        "team": "Members table with role/status columns, invite form. "
                "Pending-invitations section.",
        "login": "(Auth page — but stays in the app shell. Use the "
                 "centered-card pattern from auth_flow.)",
    },
    sitemap_pool=["overview", "detail-view", "settings", "billing",
                  "team", "login"],
    sitemap_min=6, sitemap_max=6, sitemap_first="overview",
    brand_verticals=["saas", "devtools", "fintech"],
    references=["linear.app", "vercel.com/dashboard", "planetscale.com"],
    density_override="dense",
)
