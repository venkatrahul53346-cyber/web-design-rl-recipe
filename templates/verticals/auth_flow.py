"""auth_flow (A12) — signup/login/onboarding screens."""
from templates.verticals._base import VerticalMeta

META = VerticalMeta(
    name="auth_flow",
    archetype="A12",
    difficulty="easy",
    topic_description=(
        "The signup / login / onboarding flow for a SaaS or fintech "
        "product. Each page is a single centered card. Pages are "
        "structurally sparse — minimal chrome, the form is the hero. "
        "Onboarding step pages include a step indicator (1 of N). "
        "Final dashboard-empty page has no sidebar (user is fresh). "
        "Buttons are primary-filled with the brand accent. Forms are "
        "minimal: 2-4 fields, primary CTA, link to the other auth page."
    ),
    page_hints={
        "signup": "Centered card. Brand mark on top, 'Sign up for "
                  "{brand}' headline, 1-2 social-login buttons, divider "
                  "('or continue with email'), email + password fields, "
                  "primary filled CTA, link to /login.",
        "login": "Centered card. Brand mark, 'Welcome back' or "
                 "'Sign in to {brand}', social login + email/password, "
                 "primary CTA, link to /signup + 'forgot password'.",
        "verify": "Email-verify state: large icon (envelope or "
                  "checkmark), 'check your email' message, resend link.",
        "onboarding-step-1": "Step 1 of onboarding (e.g. 'tell us "
                             "about your team'). Form. Step indicator 1/N.",
        "onboarding-step-2": "Step 2 (e.g. 'invite teammates'). Form. "
                             "Step indicator 2/N.",
        "dashboard-empty": "Empty dashboard for a fresh user. NO "
                           "sidebar yet. Centered icon + headline + "
                           "sub-copy + primary CTA ('Create your first X').",
    },
    sitemap_pool=["signup", "login", "verify",
                  "onboarding-step-1", "onboarding-step-2",
                  "dashboard-empty"],
    sitemap_min=5, sitemap_max=6, sitemap_first="signup",
    brand_verticals=["saas", "devtools", "fintech", "ai-product"],
    references=["clerk.dev", "vercel.com/login", "supabase.com/dashboard/sign-in"],
)
