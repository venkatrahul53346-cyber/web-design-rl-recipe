"""government — civic / municipal / national agency portal."""
from templates.verticals._base import VerticalMeta

META = VerticalMeta(
    name="government",
    archetype="A2",
    difficulty="hard",
    topic_description=(
        "An official site for a government agency or municipality. "
        "Visual conventions are distinctly civic: dense forms, "
        "navy-blue + accent palette, accessibility-led, breadcrumbs "
        "on every page, plain-language copy, formal typography. The "
        "site exists to help residents complete tasks (pay a bill, "
        "request a record, find a department) — NOT to sell. Tone "
        "is neutral, formal, helpful. NO marketing language, NO "
        "'free trial', NO testimonials. Pages have a lot of body "
        "text and structured forms. Headers include a search bar, "
        "language toggle, and accessibility settings link."
    ),
    page_hints={
        "index": "Civic hero — name of the agency/city + brief mission. "
                 "Below: top-tasks grid ('Pay a bill', 'Request a "
                 "record', 'Find a department'), news/announcements "
                 "section, contact strip.",
        "services": "Categorised list of services. Cards or a deep "
                    "table with category labels, plain-language "
                    "descriptions of each service.",
        "departments": "Directory of departments. Each entry: department "
                       "name, head's name + photo placeholder, contact, "
                       "link to detail page.",
        "news": "Reverse-chronological list of news/announcements. "
                "Date, headline, 1-line summary, read-more link.",
        "forms": "List of downloadable forms or online form starts. "
                 "Categorised. Each entry: form name, brief description, "
                 "link to start / download.",
        "contact": "Multi-channel contact info: phone, email, mailing "
                   "address, in-person hours, accessibility/language "
                   "support contacts.",
        "about": "Brief about-the-agency page — mission, leadership, "
                 "history. Formal tone.",
    },
    sitemap_pool=["index", "services", "departments", "news",
                  "forms", "contact", "about"],
    sitemap_min=6, sitemap_max=7,
    brand_verticals=["government"],
    references=["gov.uk", "usa.gov", "canada.ca"],
)
