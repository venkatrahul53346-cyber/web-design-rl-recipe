"""hotel_booking — boutique hotel marketing + reservation site."""
from templates.verticals._base import VerticalMeta

META = VerticalMeta(
    name="hotel_booking",
    archetype="A11",
    difficulty="hard",
    topic_description=(
        "A boutique hotel's site (independent, not a chain). The "
        "site sells stays through atmosphere, not price. Photography "
        "is essential — the experience IS visual. Index is "
        "atmospheric hero + booking widget. Rooms page has cards for "
        "each room type with photo + amenities + nightly rate. Local "
        "guide / experiences page recommends what to do nearby. "
        "Restaurant page (if the hotel has one) doubles as marketing. "
        "Reservation page is a search form (dates / guests). "
        "Aesthetic is editorial-hospitality — different from "
        "restaurant in that booking is the conversion goal."
    ),
    page_hints={
        "index": "Atmospheric full-bleed hero photo + hotel name in "
                 "display + tagline. Below: booking-widget callout "
                 "(arrive / depart / guests + 'check rates' CTA), "
                 "intro prose paragraph, photography block (3-4 "
                 "images of common areas / rooms).",
        "rooms": "Card per room type: photo, name (e.g. 'Garden "
                 "Suite'), 1-line description, key amenities (3-5 "
                 "bullets), starting rate, 'Book this room' CTA.",
        "experiences": "Curated local guide. 4-6 experience cards: "
                       "image, title, short blurb, distance/time. "
                       "Could be in-house (spa) or external (museum).",
        "restaurant": "If the hotel has a restaurant: photographic "
                      "hero + chef intro + menu glimpse + reservations "
                      "link.",
        "reservations": "Form: arrive / depart / guests / room type "
                        "(dropdown) / contact info / dietary or special "
                        "notes / submit.",
        "press": "Press mentions list + awards.",
        "about": "Hotel story / philosophy paragraph + ownership / "
                 "history.",
    },
    sitemap_pool=["index", "rooms", "experiences", "restaurant",
                  "reservations", "press", "about"],
    sitemap_min=6, sitemap_max=7,
    brand_verticals=["hospitality"],
    references=["acehotel.com", "kimptonhotels.com", "thehoxton.com"],
)
