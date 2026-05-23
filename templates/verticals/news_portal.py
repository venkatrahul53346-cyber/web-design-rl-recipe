"""news_portal — news website homepage with high information density."""
from templates.verticals._base import VerticalMeta

META = VerticalMeta(
    name="news_portal",
    archetype="A6",
    difficulty="hard",
    topic_description=(
        "A news organisation's homepage and section pages — "
        "different from longform editorial. Density is the "
        "characteristic feature: multiple stories per fold, ticker "
        "or breaking-news strip, section nav across the top, "
        "ads/promotions in the gutter, multiple typographic scales "
        "co-existing. This is read-by-everyone, throughout-the-day "
        "publication. The aesthetic is news-of-record, formal but "
        "high-energy. AVOID: long-form-only treatment, single-hero "
        "minimalism."
    ),
    page_hints={
        "index": "Top: section nav bar + breaking-news ticker. Hero: "
                 "1 lead story (large image + huge headline + dek). "
                 "Below: multi-column news grid — 6-9 secondary "
                 "stories at varying sizes, mixing image + headline "
                 "+ category tag. Sidebar with most-read list.",
        "section": "A section landing page (e.g. 'Politics', 'Tech'). "
                   "Section masthead, lead story for the section, then "
                   "grid of 8-12 stories within the section.",
        "article": "An individual news article. Less narrow than "
                   "longform — measure ~70-75ch. Photo, headline, dek, "
                   "byline, body, 'read more' related-stories block.",
        "live-blog": "A live-blog page. Reverse-chronological updates "
                     "with timestamps, latest at top, sticky 'live' "
                     "indicator.",
        "topic": "A topic page (gathering coverage of a story over "
                 "time). Topic mast, latest stories, 'background' "
                 "explainer link.",
        "video": "Video story landing — large player placeholder + "
                 "transcript / summary below + related video grid.",
    },
    sitemap_pool=["index", "section", "article", "live-blog",
                  "topic", "video"],
    sitemap_min=6, sitemap_max=6,
    brand_verticals=["media"],
    references=["theguardian.com", "nytimes.com", "ft.com"],
)
