"""portfolio_studio (A7) — design studio / creative agency portfolio."""
from templates.verticals._base import VerticalMeta

META = VerticalMeta(
    name="portfolio_studio",
    archetype="A7",
    difficulty="hard",
    topic_description=(
        "A design studio's portfolio site. The studio shows a small "
        "number of projects (case studies) and pitches new clients. "
        "The site is the studio's portfolio — every page is a "
        "deliverable in itself. Index is an oversized hero with a "
        "manifesto-style phrase. Work-index shows case-study tiles in "
        "an opinionated grid (asymmetric, varying tile sizes). Case "
        "studies are deep — title, client/year/role meta, problem, "
        "approach, outcome with imagery. About is the studio "
        "manifesto + team. Contact is oversized email link."
    ),
    page_hints={
        "index": "Oversized hero phrase / manifesto-style headline that "
                 "takes a third of the screen. Below: case-study tiles "
                 "in an asymmetric grid (3 of varying sizes, captions "
                 "below each).",
        "work-index": "More case-study tiles. Possibly hover-state "
                      "implied by larger thumbnail. Filter by category "
                      "(brand / digital / motion).",
        "case-study-A": "Title, meta (client / year / role) block, "
                        "problem statement, hero image, approach, "
                        "outcome with images interspersed.",
        "case-study-B": "Same shape as case-study-A, different project "
                        "(different client + different visual approach).",
        "about": "Studio manifesto / philosophy paragraph, team grid "
                 "(4-8 placeholder people), services list.",
        "contact": "Oversized email link. Address, social links, "
                   "perhaps an inquiry form.",
    },
    sitemap_pool=["index", "work-index", "case-study-A",
                  "case-study-B", "about", "contact"],
    sitemap_min=6, sitemap_max=6,
    brand_verticals=["agency"],
    references=["basicagency.com", "locomotive.ca", "areweb.studio"],
)
