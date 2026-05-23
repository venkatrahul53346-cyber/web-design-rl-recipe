"""healthcare_clinic — clinic / hospital / telehealth site."""
from templates.verticals._base import VerticalMeta

META = VerticalMeta(
    name="healthcare_clinic",
    archetype="A2",
    difficulty="medium",
    topic_description=(
        "A healthcare provider site — could be a clinic, hospital "
        "system, or telehealth service. The aesthetic is calming "
        "(soft blue / teal palette), professional, photography-led "
        "but with natural / human imagery (not stock-doctor). The "
        "primary jobs are: explain what services we offer, find a "
        "doctor, book an appointment, log into the patient portal. "
        "Tone is reassuring, plain-language. AVOID: aggressive "
        "marketing, high-saturation accents, busy layouts."
    ),
    page_hints={
        "index": "Calming hero — natural human image + headline like "
                 "'Better care, closer to home' + primary CTA "
                 "('Book an appointment'). Below: services-grid "
                 "(3-4 categories), 'find a doctor' block, recent-news "
                 "/ patient-stories section, locations strip.",
        "services": "List of services / specialties — "
                    "cards by category (cardiology, pediatrics, etc.) "
                    "with brief description and 'learn more' link.",
        "find-a-doctor": "Search filters (specialty, location, "
                         "language, accepting-new-patients) + grid of "
                         "doctor cards (photo, name, specialty, link).",
        "patient-portal": "Login-card pattern (similar to auth_flow): "
                          "email + password + login + 'don't have an "
                          "account?' link. Brand reassurance copy.",
        "locations": "Map/list of locations. Each entry: address, "
                     "phone, hours, services available, accepting-"
                     "new-patients flag.",
        "about": "Mission paragraph, leadership / quality stats "
                 "(awards, accreditations), patient-experience pillars.",
        "appointment": "Appointment-request form: provider, type, "
                       "preferred date/time, contact info, notes.",
    },
    sitemap_pool=["index", "services", "find-a-doctor", "patient-portal",
                  "locations", "about", "appointment"],
    sitemap_min=6, sitemap_max=7,
    brand_verticals=["healthcare"],
    references=["clevelandclinic.org", "mayoclinic.org", "onemedical.com"],
)
