"""editorial_pub (A6) — independent magazine / longform publication."""
from templates.verticals._base import VerticalMeta

META = VerticalMeta(
    name="editorial_pub",
    archetype="A6",
    difficulty="hard",
    topic_description=(
        "An independent longform publication — articles of 600-2000 "
        "words, published less often than a daily news site. The site "
        "is read by adults who pay (subscribe / donate). Index is an "
        "editorial cover with one hero article + 4-6 secondary cards. "
        "Article pages have a lead photo, oversized headline, byline, "
        "narrow measure for body, and end with author bio + related "
        "reads. NO sidebars during article body. The aesthetic is "
        "considered, not breaking-news."
    ),
    page_hints={
        "index": "Editorial cover. Hero article: large image + "
                 "headline + dek + byline. Then 4-6 secondary articles "
                 "in a sparse grid (image + headline + tag).",
        "article-A": "Long-form article. Lead photo (full-bleed or "
                     "wide), oversized headline, dek (lighter weight), "
                     "byline + date, narrow-measure body, optional drop "
                     "cap or all-caps lede, one pull quote, author bio "
                     "+ related-reads at the end.",
        "article-B": "Same shape as article-A but different content "
                     "(different topic / structure).",
        "author-page": "Simple list of articles by one author, with "
                       "thumbnails. Author photo + bio above the list.",
        "tag-page": "List of articles in one tag/category. Header for "
                    "the tag + list of articles with thumbnails.",
        "about": "Short masthead — who runs the publication, how often "
                 "it publishes, where to subscribe.",
    },
    sitemap_pool=["index", "article-A", "article-B", "author-page",
                  "tag-page", "about"],
    sitemap_min=6, sitemap_max=6,
    brand_verticals=["media"],
    references=["every.to", "theverge.com/features", "harpers.org"],
)
