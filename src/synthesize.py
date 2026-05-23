"""Phase 2 synthesis pipeline driver — per-page architecture.

Two-stage compile via Claude Opus 4.7:

  Stage 1 (design pass): WebsiteSpec → {styles.css, nav_html, footer_html,
    design_brief}. One Anthropic call. ~3-5K output tokens.

  Stage 2 (per-page passes, one per page in sitemap): WebsiteSpec +
    design from stage 1 + page-purpose guidance → one .html file.
    ~2-4K output tokens each.

Total: 1 + N calls (N=5-7 pages). Avoids the 32K-tokens-per-call cap
that single-shot generation hit on content-heavy archetypes (docs sites
with code blocks easily exceed 32K total).

Stage-1 design context is passed verbatim to every stage-2 call so all
pages share the same nav/footer markup and reference the same CSS classes.

Usage:

    ANTHROPIC_API_KEY="$(tr -d '\\n\\r' < ~/.trial-anthropic-key)" \\
        .venv/bin/python -m src.synthesize \\
            --slot devdocs-mono \\
            --out datasets/synth/devdocs-mono-001 \\
            --force
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import shutil
import sys
import tempfile
import textwrap
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from anthropic import Anthropic
from playwright.sync_api import sync_playwright

from src.generate import build_task_dir
from src.render import render_site
from src.spec import WebsiteSpec


COMPILER_MODEL = "claude-opus-4-7"
DESIGN_MAX_TOKENS = 16000   # design + CSS + shared markup (dashboard_dense css runs ~12K)
PAGE_MAX_TOKENS = 20000     # rich pages (docs with code blocks) need ~10-15K


# ---------------------------------------------------------------------------
# Anti-patterns (the "AI tells") shared between both passes' system prompts.
# ---------------------------------------------------------------------------

ANTI_PATTERNS = textwrap.dedent("""\
    CRITICAL — AVOID THESE "AI-GENERATED TELLS":

    1. Uniform vertical rhythm. Do NOT use the same `padding: 96px` /
       `py-16` on every section. Vary section padding for hierarchy.
    2. Single font family at four weights. If the spec asks for
       display-mixed or two distinct typefaces, ACTUALLY use two.
    3. Snap-to-12-col grid for everything. Use asymmetric grids,
       overlapping elements, edge-bleeds when the design calls for it.
    4. `border-radius: 12px` and `box-shadow: 0 1px 2px rgba(0,0,0,0.05)`
       on every card regardless of brand. Match the spec's border_language.
    5. Default 3-stop linear gradient hero. If motif is clean-iconographic,
       NO gradient blobs.
    6. Always-centered headlines. Edge-aligned, oversized-display
       headlines are valid and often better.
    7. Default Tailwind grays when a brand palette is specified.
    8. The "shadcn template": hero → 3-feature-grid → testimonials → CTA.
       Vary section types, order, and layout per archetype.
    9. Pastel-on-white regardless of color_regime. Match the regime.
    10. Lorem ipsum / "Feature one — Description". Write real copy.
    """)


# ---------------------------------------------------------------------------
# Stage 1: design pass.
# ---------------------------------------------------------------------------

DESIGN_SYSTEM_PROMPT = textwrap.dedent("""\
    You are a senior frontend engineer designing a real product website.
    Your output must look like a contemporary handmade design from a small
    design-conscious team — NOT an AI-generated template.

    THIS IS THE DESIGN PASS. You will produce the SHARED design system —
    the stylesheet and the shared header/footer markup — that every page
    of the site will reuse.

    """) + ANTI_PATTERNS + textwrap.dedent("""\

    OUTPUT FORMAT (REQUIRED):

    Respond with a single ```json fenced code block containing:

    ```json
    {
      "styles_css": "@import url(...);\\n:root { --bg: ... }\\n...",
      "nav_html":   "<header class=\\"site-header\\">...</header>",
      "footer_html":"<footer class=\\"site-footer\\">...</footer>",
      "design_brief": "Plain-text summary of design tokens and conventions: \\
                       background colors, accent, typography scale, border style, \\
                       spacing rhythm, common component patterns. Used to keep \\
                       the per-page passes consistent."
    }
    ```

    Requirements:
    - styles_css must include @import for fonts (or use system stack), CSS
      variables for the design tokens, body/typography defaults, and styles
      for the nav/header, footer, AND every visual pattern that pages will
      need (cards, buttons, sections, code blocks, tables, etc.). Pages will
      reuse these classes — do NOT redefine tokens per-page later.
    - nav_html and footer_html must be complete fragments (no <!DOCTYPE>),
      ready to embed inside any page's <body>. They should reference the
      classes you defined in styles_css. Include real brand-appropriate
      navigation links and footer columns — no "Link 1 / Link 2" filler.
    - design_brief is plain text (not HTML), 200-400 words, describing the
      visual language so the per-page generator can match it.

    Output the raw JSON inside ```json``` — no preamble, no commentary.
    """)


def _build_design_user_prompt(spec: WebsiteSpec) -> str:
    style = spec.style
    fonts = ", ".join(f for f in spec.font_pair if f) if spec.font_pair else "system-ui"
    notes_block = (
        f"\n\nAdditional design notes:\n{spec.notes}\n"
        if spec.notes else ""
    )
    sitemap_str = ", ".join(f"{p}.html" for p in spec.sitemap)
    return textwrap.dedent(f"""\
        WEBSITE SPEC

        Brand: {spec.brand.name}
        Tagline: "{spec.brand.tagline}"
        Value proposition: {spec.brand.value_prop}
        Product category: {spec.brand.product_category}
        Target audience: {spec.brand.target_audience}

        Archetype: {spec.archetype} ({spec.vertical} vertical).
        Difficulty: {spec.difficulty}.

        STYLE AXES (all five must be reflected in the design):
        - Density: {style.density}
        - Color regime: {style.color_regime}
        - Typography: {style.typography}
        - Border language: {style.border_language}
        - Motif: {style.motif}

        Palette seed: {spec.palette_seed}
        Fonts: {fonts}.

        The full sitemap will be: {sitemap_str}, plus styles.css.
        Pages will be generated in subsequent passes; this pass produces
        ONLY the shared design system + nav + footer.{notes_block}

        Now produce the design-pass JSON described in the system prompt.
        """)


# ---------------------------------------------------------------------------
# Stage 2: per-page passes.
# ---------------------------------------------------------------------------

PAGE_SYSTEM_PROMPT = textwrap.dedent("""\
    You are a senior frontend engineer designing a real product website.
    The design system (CSS, nav, footer, conventions) has already been
    decided. Your job is to produce ONE page's HTML, consistent with
    that design system.

    """) + ANTI_PATTERNS + textwrap.dedent("""\

    OUTPUT FORMAT (REQUIRED):

    Respond with a single ```json fenced code block containing:

    ```json
    {
      "page_html": "<!DOCTYPE html>...complete HTML5 document..."
    }
    ```

    The page_html must:
    - Be a complete, valid HTML5 document.
    - Link styles.css via `<link rel="stylesheet" href="styles.css">`.
    - Have a meaningful <title> reflecting THIS page's purpose.
    - Embed the provided nav_html (apply an "active" class if your design
      has one) and footer_html exactly as given (don't redesign them).
    - Use the CSS classes already defined in styles.css. Don't add
      <style> blocks unless you need a one-off rule for this page.
    - Have content specific to THIS page's purpose — different from the
      other pages of the same site.
    - Include real, brand-appropriate visible text — never lorem ipsum.
    - For images, you may either reference "rick.jpg" (placeholder) or
      omit images.

    Output the raw JSON inside ```json``` — no preamble, no commentary.
    """)


# Per-page guidance — what each page should contain. Default is "follow the
# archetype's typical structure" if a page isn't in this dict.
PAGE_PURPOSES = {
    "index":           "Landing page. Hero (brand value prop, single CTA), then 2-4 distinct sections that demonstrate the product. Avoid the 'shadcn template' default.",
    "features":        "Deep dive into capabilities. 4-6 feature blocks alternating image/diagram-left vs text-right, each focused on one capability with concrete benefits.",
    "pricing":         "Tier comparison. 2-4 plans side-by-side with feature checkmarks. Highlight one recommended tier visually.",
    "customers":       "Social proof: testimonial quotes, customer logos cluster, 1-2 short case-study cards. Real names + titles + companies (made up but plausible).",
    "about":           "Company narrative: mission paragraph, founding-story paragraph, team grid (4-8 placeholder people with roles), values list.",
    "contact":         "Contact form (name, email, message), office addresses (real-feeling cities), support channel links, footer info.",
    "getting-started": "Quickstart guide. Install command in code block, minimal hello-world example, then next-steps links. Code blocks must be visually distinct (tinted bg, mono font).",
    "api-reference":   "API endpoint or function reference. Show 2-3 endpoints/functions with: signature, parameter table, request example (code block), response example (code block).",
    "guides":          "List of cookbook recipes. 4-6 guide cards with title + 1-line description, leading to detailed steps. The detail itself can be summarised.",
    "examples":        "Code-heavy. 3-5 self-contained integration snippets in different languages or for different use-cases. Each snippet ~10-30 lines in a code block, with prose explanation.",
    "changelog":       "Reverse-chronological list. Each entry: version number + date + bullet-point changes. 5-8 entries spanning a few months.",
    "menu":            "Restaurant menu. Sections (starters / mains / drinks / dessert), dish names, descriptions, prices. Photographic if motif allows.",
    "reservations":    "Reservation form: date/time/party-size pickers, dietary-restriction notes, contact field.",
    "location":        "Address, hours table (day-of-week × hours), embedded-map placeholder, parking/transit notes.",
    "press":           "Press logos cluster, recent media mentions list, press-kit download links, press contact.",
    "story":           "Splash narrative page: long-form story about the product, scroll-driven sections with oversized type and minimal chrome.",
    "specs":           "Product specifications table or sections: dimensions, materials, technical capabilities. Image-led.",
    "preorder":        "Preorder form / waiting list: hero CTA, form, FAQ.",
    "faq":             "FAQ accordion or grouped Q&A. 8-15 entries.",
    "thread-index":    "Forum/changelog list: vertical list of threads/posts with title, author, date, reply-count.",
    "thread-detail":   "Single thread/post detail: title, body, comments threaded below.",
    "user-profile":    "User profile: avatar, bio, contributions list.",
    "rules":           "Community rules / TOS-style page: numbered or sectioned rules, formal tone.",
    "signup":          "Signup form: email/password, branding, link to login.",
    "login":           "Login form: minimal, link to signup, branding.",
    "verify":          "Email verify state: large icon, 'check your email' message.",
    "onboarding-step-1":"Onboarding step 1: e.g. 'tell us about your team', form.",
    "onboarding-step-2":"Onboarding step 2: e.g. 'invite teammates', step indicator showing 2 of N.",
    "dashboard-empty": "Empty dashboard: minimal sidebar, empty state with CTA.",
    "overview":        "Dashboard overview: KPI cards, charts, recent activity feed.",
    "detail-view":     "Dashboard detail: data table with filters, header, breadcrumbs.",
    "settings":        "Settings page: sidebar of categories, current category form on right.",
    "billing":         "Billing: current plan card, invoice history table, payment-method on file.",
    "team":            "Team management: members table with role/status columns, invite form.",
    "collection":      "E-commerce category page: product grid with filters in left rail.",
    "PDP":             "E-commerce product detail page: large image, price, variants, add-to-cart, description.",
    "cart":            "E-commerce cart: line items, subtotal, checkout CTA.",
    "journal":         "Editorial journal listing: posts grid with featured image, title, excerpt.",
    "compare":         "Pricing comparison page: full feature-by-tier matrix.",
    "work-index":      "Portfolio work index: case-study tiles in an opinionated grid.",
    "case-study-A":    "Portfolio case study: title, problem, approach, outcome with images.",
    "case-study-B":    "Portfolio case study (different from A): title, problem, approach, outcome.",
    "article-A":       "Editorial article: serif body, ~800 words, drop cap, pull quote, photo.",
    "article-B":       "Different editorial article: ~600 words, structured differently from A.",
    "author-page":     "Editorial author page: bio, photo, list of articles by this author.",
    "tag-page":        "Editorial tag/category index: header for the tag, list of articles in it.",
    "use-cases":       "Product use-cases: 3-5 named use-case cards, each with persona + benefit.",
    "how-it-works":    "Product how-it-works: 3-5 numbered steps explaining the workflow, with diagrams or screenshots.",
    "product-overview":"Product overview: top-level description with 2-3 key sections.",
    "docs-link":       "Bridge page: links out to the docs / community / API reference, with brief context.",
}


def _build_page_user_prompt(spec: WebsiteSpec, design: Dict[str, str],
                            page_name: str) -> str:
    purpose = PAGE_PURPOSES.get(
        page_name,
        f"Build content appropriate for a page named '{page_name}' in a "
        f"{spec.archetype} {spec.vertical} site."
    )
    return textwrap.dedent(f"""\
        WEBSITE CONTEXT

        Brand: {spec.brand.name} — "{spec.brand.tagline}"
        Value prop: {spec.brand.value_prop}
        Product category: {spec.brand.product_category}
        Target audience: {spec.brand.target_audience}
        Archetype: {spec.archetype} ({spec.vertical}). Difficulty: {spec.difficulty}.

        DESIGN BRIEF (the visual language for this site):
        {design.get("design_brief", "")}

        SHARED HEADER (embed verbatim, with active state if applicable):
        ```html
        {design.get("nav_html", "")}
        ```

        SHARED FOOTER (embed verbatim):
        ```html
        {design.get("footer_html", "")}
        ```

        STYLES.CSS (already exists; reference its classes — do NOT redefine
        design tokens; you may add minimal page-specific rules in a
        `<style>` block at the end of <head> if absolutely necessary):
        ```css
        {design.get("styles_css", "")[:8000]}
        ```

        NOW PRODUCE THE PAGE: {page_name}.html

        Page purpose: {purpose}

        The HTML must be a complete <!DOCTYPE html5> document with
        <link rel="stylesheet" href="styles.css">, <title> appropriate to
        this page, the shared header inside <body>, page content in
        appropriate sections/main, and the shared footer at the bottom.

        Output the raw JSON described in the system prompt.
        """)


# ---------------------------------------------------------------------------
# JSON extraction (same as before).
# ---------------------------------------------------------------------------

_JSON_BLOCK = re.compile(r"```(?:json)?\s*(\{.*\})\s*```", re.DOTALL)


def _extract_json(text: str, label: str = "synth") -> Dict:
    debug_path = Path("/tmp") / f"last-{label}-response.txt"
    debug_path.write_text(text)
    raw = None
    m = _JSON_BLOCK.search(text)
    if m:
        raw = m.group(1)
    else:
        first = text.find("{")
        last = text.rfind("}")
        if first >= 0 and last > first:
            raw = text[first:last + 1]
    if raw is None:
        raise ValueError(f"no JSON in response, saved to {debug_path}")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"JSON parse failed ({exc}). Saved to {debug_path}"
        ) from None


# ---------------------------------------------------------------------------
# LLM call (streaming).
# ---------------------------------------------------------------------------

def _stream_call(client: Anthropic, model: str, max_tokens: int,
                 system: str, user: str, label: str) -> Tuple[str, int, int]:
    """Returns (text, input_tokens, output_tokens). Raises on max_tokens hit."""
    return _stream_call_messages(
        client, model, max_tokens, system,
        [{"role": "user", "content": user}], label,
    )


def _stream_call_messages(client: Anthropic, model: str, max_tokens: int,
                          system: str, messages: List[Dict],
                          label: str) -> Tuple[str, int, int]:
    """Multi-turn variant of _stream_call with transient-error retry.

    Anthropic streams over HTTP/2 occasionally drop mid-response (httpx
    RemoteProtocolError, connection reset, server-side 5xx). We retry up
    to 2 times with backoff before raising — these are transport failures
    that should NOT consume one of the iterative-loop's iteration slots.
    """
    import time
    import httpx
    import anthropic as _anthropic_mod

    transient = (
        httpx.RemoteProtocolError,
        httpx.ReadError,
        httpx.ConnectError,
        httpx.ReadTimeout,
        httpx.WriteError,
        _anthropic_mod.APIConnectionError,
        _anthropic_mod.APITimeoutError,
    )

    last_exc: Optional[BaseException] = None
    for attempt in range(3):           # initial + 2 retries
        try:
            return _stream_call_messages_once(
                client, model, max_tokens, system, messages, label,
            )
        except transient as exc:
            last_exc = exc
            if attempt == 2:
                break
            backoff = 1 * (4 ** attempt)   # 1s, 4s
            print(
                f"    [transport-retry {attempt+1}/2 for {label}] "
                f"{type(exc).__name__}: {exc} (sleeping {backoff}s)",
                flush=True,
            )
            time.sleep(backoff)
    raise RuntimeError(
        f"{label}: transport error after 3 attempts (last: "
        f"{type(last_exc).__name__}: {last_exc}). Network or upstream "
        f"issue, not a content problem."
    ) from last_exc


def _stream_call_messages_once(client: Anthropic, model: str, max_tokens: int,
                               system: str, messages: List[Dict],
                               label: str) -> Tuple[str, int, int]:
    """Single attempt — original _stream_call_messages body."""
    chunks: List[str] = []
    stop_reason = None
    usage_in = usage_out = 0
    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    ) as stream:
        for chunk in stream.text_stream:
            chunks.append(chunk)
        final = stream.get_final_message()
        stop_reason = final.stop_reason
        usage_in = final.usage.input_tokens
        usage_out = final.usage.output_tokens
    text = "".join(chunks)
    if stop_reason == "max_tokens":
        debug_path = Path("/tmp") / f"truncated-{label}.txt"
        debug_path.write_text(text)
        raise RuntimeError(
            f"{label} hit max_tokens={max_tokens} ({usage_out} output tokens). "
            f"Saved to {debug_path}."
        )
    return text, usage_in, usage_out


# ---------------------------------------------------------------------------
# Per-page validation: format checks + render-time checks.
# ---------------------------------------------------------------------------

# Viewports the page is rendered + checked at during validation. The
# mobile pass is what catches the "horizontal overflow / no viewport
# meta" failure modes that bite v3.4 mobile scoring.
_VALIDATION_VIEWPORTS = [
    {"name": "desktop", "width": 1280, "height": 800},
    {"name": "mobile",  "width":  390, "height": 844},
]
_MOBILE_OVERFLOW_TOLERANCE_PX = 20   # 390 + 20 = 410 OK
_MIN_PAGE_HEIGHT = 200               # below this is "blank or collapsed"
_MIN_CONTENT_COVERAGE = 0.03         # ≥3% non-white pixels at desktop


ALLOWED_IMAGE_SRCS = frozenset({
    "photo-product-1.jpg",
    "photo-product-2.jpg",
    "photo-portrait-1.jpg",
    "photo-landscape-1.jpg",
    "illustration-abstract.jpg",
})


def _validate_page_format(page_html: str, page_name: str) -> List[str]:
    """Cheap text-only format checks — no rendering needed."""
    issues: List[str] = []
    if not page_html.lstrip().lower().startswith("<!doctype"):
        issues.append(
            f"`{page_name}` doesn't start with <!DOCTYPE html>. "
            f"Add `<!DOCTYPE html>` as the very first line."
        )
    if 'href="styles.css"' not in page_html and "href='styles.css'" not in page_html:
        issues.append(
            f"`{page_name}` doesn't link to styles.css. Add "
            f'`<link rel="stylesheet" href="styles.css">` in <head>.'
        )
    # Validate <img> sources are in the allow-list
    img_srcs = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', page_html)
    bad = [s for s in img_srcs if s not in ALLOWED_IMAGE_SRCS]
    if bad:
        unique_bad = sorted(set(bad))
        issues.append(
            f"`{page_name}` uses disallowed image src(s): {unique_bad}. "
            f"Replace each `<img src=\"X\">` with one of the allowed "
            f"placeholders ({sorted(ALLOWED_IMAGE_SRCS)}), or remove the "
            f"<img> entirely and use CSS gradient / inline SVG / styled "
            f"<div> for decorative content."
        )
    return issues


def _validate_page_runtime(page_html: str, page_name: str,
                           design: Dict[str, str],
                           scratch_dir: Path) -> List[str]:
    """Render the page at desktop and mobile, run sanity checks. Returns
    a list of human-readable issue strings (empty list = passes).

    Issues come with **specific, actionable** fix hints — the LLM uses
    these on retry.
    """
    issues: List[str] = []
    page_path = scratch_dir / page_name
    page_path.write_text(page_html)
    css_path = scratch_dir / "styles.css"
    if not css_path.exists():
        css_path.write_text(design.get("styles_css", ""))

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        try:
            for vp in _VALIDATION_VIEWPORTS:
                ctx = browser.new_context(
                    viewport={"width": vp["width"], "height": vp["height"]},
                    device_scale_factor=1,
                )
                pg = ctx.new_page()
                try:
                    pg.goto(page_path.as_uri(), wait_until="load", timeout=15000)
                    pg.wait_for_timeout(150)
                    metrics = pg.evaluate(
                        "() => ({ "
                        "scrollWidth: document.documentElement.scrollWidth, "
                        "scrollHeight: document.documentElement.scrollHeight, "
                        "clientWidth: document.documentElement.clientWidth, "
                        "hasViewportMeta: !!document.querySelector('meta[name=\"viewport\"]') "
                        "})"
                    )

                    if vp["name"] == "mobile":
                        max_ok = vp["width"] + _MOBILE_OVERFLOW_TOLERANCE_PX
                        if metrics["scrollWidth"] > max_ok:
                            issues.append(
                                f"[mobile {vp['width']}×{vp['height']}] Horizontal "
                                f"overflow: page width is {metrics['scrollWidth']}px "
                                f"but viewport is only {vp['width']}px. The page "
                                f"requires sideways scrolling on mobile, which is "
                                f"a critical responsiveness bug. Common causes: "
                                f"(1) hardcoded `width: <some-large-px>` in CSS — "
                                f"replace with `max-width:` and percentage / `1fr` / "
                                f"`auto`; (2) flex containers without `flex-wrap: wrap`; "
                                f"(3) images without `max-width: 100%; height: auto`; "
                                f"(4) tables without responsive treatment (wrap them in "
                                f"`overflow-x: auto` containers or use display flex). "
                                f"Add `@media (max-width: 768px) {{ ... }}` queries to "
                                f"switch to a stacked / single-column layout."
                            )
                        if not metrics["hasViewportMeta"]:
                            issues.append(
                                f'[mobile] Missing `<meta name="viewport">` tag in <head>. '
                                f'This causes mobile browsers to render the page at '
                                f'desktop width and zoom out, making everything tiny. '
                                f'Add: '
                                f'`<meta name="viewport" content="width=device-width, '
                                f'initial-scale=1.0">` inside <head>.'
                            )
                    elif vp["name"] == "desktop":
                        if metrics["scrollHeight"] < _MIN_PAGE_HEIGHT:
                            issues.append(
                                f"[desktop {vp['width']}×{vp['height']}] Page is too "
                                f"short ({metrics['scrollHeight']}px) — likely empty "
                                f"or content collapsed. Make sure <body> has visible "
                                f"content (sections, paragraphs, headings) appropriate "
                                f"for {page_name}."
                            )
                        # Content-coverage check on the desktop screenshot
                        shot = scratch_dir / f"_validate_{page_name}.{vp['name']}.png"
                        pg.screenshot(path=str(shot), full_page=True)
                        try:
                            from PIL import Image
                            import numpy as np
                            img = np.asarray(Image.open(shot).convert("L"))
                            coverage = float((img < 240).mean())
                            if coverage < _MIN_CONTENT_COVERAGE:
                                issues.append(
                                    f"[desktop] Page is mostly blank: only "
                                    f"{coverage:.1%} of pixels are non-white "
                                    f"(threshold {_MIN_CONTENT_COVERAGE:.0%}). "
                                    f"Add real visible content matching the page's "
                                    f"purpose."
                                )
                        except Exception:
                            pass
                except Exception as exc:
                    issues.append(
                        f"[{vp['name']}] Page failed to render: {exc}. "
                        f"Check for syntax errors in HTML or unbalanced tags."
                    )
                finally:
                    ctx.close()
        finally:
            browser.close()

    return issues


def _format_validation_feedback(issues: List[str], page_name: str) -> str:
    """Compose the user-turn message that asks the LLM to fix the issues."""
    bullets = "\n".join(f"  - {i}" for i in issues)
    return textwrap.dedent(f"""\
        Your `{page_name}` failed these validation checks when rendered:

        {bullets}

        Please return a corrected version. The output format is the same:
        a single ```json``` block with the `page_html` key. The page must
        render correctly at both 1280×800 (desktop) and 390×844 (mobile),
        be a complete <!DOCTYPE html5> document, link to styles.css, and
        include a `<meta name="viewport">` tag.

        Focus your changes on the specific issues listed above. Keep
        everything else (semantic structure, content, branding) consistent
        with what you produced previously.
        """)


# ---------------------------------------------------------------------------
# Iterative per-page compile.
# ---------------------------------------------------------------------------

PAGE_MAX_ITERATIONS = 2  # initial attempt + up to 1 correction


def _page_pass_iterative(
    client: Anthropic, spec: WebsiteSpec, design: Dict[str, str],
    page_name: str, model: str = COMPILER_MODEL,
    max_iters: int = PAGE_MAX_ITERATIONS,
) -> Tuple[str, int, int, int]:
    """Multi-turn page compile with feedback loop.

    Sends the initial page-pass prompt; if validation (format + render-
    time at desktop and mobile) fails, appends an assistant turn with the
    LLM's last output and a user turn with specific failure messages,
    then loops up to ``max_iters`` times. Returns
    ``(page_html, total_input_tokens, total_output_tokens, iters_used)``.
    """
    initial_user = _build_page_user_prompt(spec, design, page_name)
    messages: List[Dict[str, str]] = [{"role": "user", "content": initial_user}]

    total_in = total_out = 0
    last_issues: List[str] = []
    last_html: str = ""

    with tempfile.TemporaryDirectory(prefix=f"validate-{spec.slug}-") as scratch:
        scratch_dir = Path(scratch)

        for iter_n in range(1, max_iters + 1):
            label = f"{spec.slug}-{page_name}-iter{iter_n}"
            text, ti, to = _stream_call_messages(
                client, model, PAGE_MAX_TOKENS,
                PAGE_SYSTEM_PROMPT, messages, label,
            )
            total_in += ti
            total_out += to

            # Parse files
            try:
                data = _extract_json(text, label=label)
            except ValueError as exc:
                # JSON parse failed — feed back as an issue and re-ask
                messages.append({"role": "assistant", "content": text})
                messages.append({
                    "role": "user",
                    "content": (
                        f"Your response could not be parsed as JSON ({exc}). "
                        f"Return only a single ```json``` code block with "
                        f'the structure: {{"page_html": "<!DOCTYPE html>..."}}.'
                    ),
                })
                last_issues = [f"JSON parse failed: {exc}"]
                continue

            if "page_html" not in data:
                messages.append({"role": "assistant", "content": text})
                messages.append({
                    "role": "user",
                    "content": (
                        "Response was missing the `page_html` key. "
                        'Return JSON of the form `{"page_html": "<!DOCTYPE html>..."}`.'
                    ),
                })
                last_issues = ["missing 'page_html' key"]
                continue

            page_html = data["page_html"]
            last_html = page_html

            # Validate
            format_issues = _validate_page_format(page_html, f"{page_name}.html")
            runtime_issues = _validate_page_runtime(
                page_html, f"{page_name}.html", design, scratch_dir,
            )
            all_issues = format_issues + runtime_issues

            if not all_issues:
                return page_html, total_in, total_out, iter_n

            # Log what we found and ask for a fix
            print(f"    iter {iter_n}: {len(all_issues)} validation issue(s)",
                  flush=True)
            for issue in all_issues:
                print(f"      - {issue[:140]}", flush=True)
            messages.append({"role": "assistant", "content": text})
            messages.append({
                "role": "user",
                "content": _format_validation_feedback(all_issues, page_name),
            })
            last_issues = all_issues

    # Exhausted iterations — log final state and accept the last attempt.
    # Raising here would kill the entire synth run for one validation miss
    # on one page; with max_iters=1 (the default), that's far too brittle.
    debug_path = Path("/tmp") / f"page-pass-failed-{spec.slug}-{page_name}.html"
    debug_path.write_text(last_html or "")
    print(
        f"    {page_name}: validation failed after {max_iters} iter(s); "
        f"accepting best-effort output. Issues:",
        flush=True,
    )
    for issue in last_issues:
        print(f"      - {issue[:160]}", flush=True)
    print(f"      (saved to {debug_path})", flush=True)
    return last_html, total_in, total_out, max_iters


# ---------------------------------------------------------------------------
# Validation (whole-task format level — uses iterative output).
# ---------------------------------------------------------------------------

def _validate_files(files: Dict[str, str], spec: WebsiteSpec) -> List[str]:
    issues: List[str] = []
    expected_html = {f"{p}.html" for p in spec.sitemap}
    actual_html = {n for n in files if n.endswith(".html")}
    missing = expected_html - actual_html
    extra = actual_html - expected_html
    if missing:
        issues.append(f"missing HTML pages: {sorted(missing)}")
    if extra:
        issues.append(f"extra HTML pages (not in sitemap): {sorted(extra)}")
    if "styles.css" not in files:
        issues.append("missing styles.css")
    for name, content in files.items():
        if not name.endswith((".html", ".css")):
            issues.append(f"unexpected non-HTML/CSS file: {name}")
        if name.endswith(".html"):
            if not content.lstrip().lower().startswith("<!doctype"):
                issues.append(f"{name} doesn't start with <!DOCTYPE>")
            if 'href="styles.css"' not in content and "href='styles.css'" not in content:
                issues.append(f"{name} doesn't link styles.css")
    return issues


# ---------------------------------------------------------------------------
# Top-level compiler — design pass + per-page passes.
# ---------------------------------------------------------------------------

def call_compiler(spec: WebsiteSpec, *, model: str = COMPILER_MODEL) -> Dict[str, str]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit(
            "ANTHROPIC_API_KEY not set. Run with:\n"
            "  ANTHROPIC_API_KEY=\"$(tr -d '\\n\\r' < ~/.trial-anthropic-key)\" "
            "python -m src.synthesize ..."
        )
    client = Anthropic(api_key=api_key)

    print(f"  compiler [design pass]…", flush=True)
    text, ti, to = _stream_call(
        client, model, DESIGN_MAX_TOKENS,
        DESIGN_SYSTEM_PROMPT, _build_design_user_prompt(spec),
        label=f"{spec.slug}-design",
    )
    design = _extract_json(text, label=f"{spec.slug}-design")
    for k in ("styles_css", "nav_html", "footer_html", "design_brief"):
        if k not in design:
            raise RuntimeError(f"design pass missing key '{k}'")
    print(f"    design ok: tokens in={ti} out={to}, css={len(design['styles_css'])}b", flush=True)

    files: Dict[str, str] = {"styles.css": design["styles_css"]}
    total_in, total_out = ti, to

    for page_name in spec.sitemap:
        print(f"  compiler [page {page_name}] (iterative)…", flush=True)
        page_html, ti, to, iters = _page_pass_iterative(
            client, spec, design, page_name, model=model,
        )
        files[f"{page_name}.html"] = page_html
        total_in += ti
        total_out += to
        print(f"    {page_name} ok in {iters} iter(s): tokens in={ti} out={to}", flush=True)

    issues = _validate_files(files, spec)
    if issues:
        debug_path = Path("/tmp") / f"synthesize-debug-{spec.slug}.json"
        debug_path.write_text(json.dumps(
            {"issues": issues, "files": files}, indent=2
        ))
        raise RuntimeError(
            f"Compiler output failed validation ({len(issues)} issues):\n  - "
            + "\n  - ".join(issues)
            + f"\nDebug dump: {debug_path}"
        )

    print(f"  compiler ok: {len(files)} files, total tokens in={total_in} out={total_out}", flush=True)
    return files


# ---------------------------------------------------------------------------
# End-to-end synthesize (unchanged from before).
# ---------------------------------------------------------------------------

PLACEHOLDER_DIR = Path(__file__).resolve().parent.parent / "templates" / "_placeholders"


def _placeholder_assets() -> Dict[str, Path]:
    """Return {filename: source_path} for the 5 bundled placeholder JPGs.
    Wired into every task's environment/assets/ via build_task_dir."""
    if not PLACEHOLDER_DIR.is_dir():
        raise RuntimeError(
            f"placeholder dir missing: {PLACEHOLDER_DIR}. Run "
            f"`python scripts/build_placeholders.py` to generate it."
        )
    files = {
        "photo-product-1.jpg":      PLACEHOLDER_DIR / "photo-product-1.jpg",
        "photo-product-2.jpg":      PLACEHOLDER_DIR / "photo-product-2.jpg",
        "photo-portrait-1.jpg":     PLACEHOLDER_DIR / "photo-portrait-1.jpg",
        "photo-landscape-1.jpg":    PLACEHOLDER_DIR / "photo-landscape-1.jpg",
        "illustration-abstract.jpg": PLACEHOLDER_DIR / "illustration-abstract.jpg",
    }
    for name, path in files.items():
        if not path.is_file():
            raise RuntimeError(f"placeholder file missing: {path}")
    return files


def synthesize_task(spec: WebsiteSpec, out_dir: Path,
                    force: bool = False) -> Path:
    print(f"[{spec.slug}] compiling spec via {COMPILER_MODEL}…")
    files = call_compiler(spec)

    print(f"[{spec.slug}] rendering screenshots on host…")
    with tempfile.TemporaryDirectory(prefix="synth-") as tmpdir:
        scratch = Path(tmpdir)
        for name, content in files.items():
            (scratch / name).write_text(content)
        # Copy placeholder JPGs into scratch so render_site sees them — agent
        # HTML references e.g. <img src="photo-product-1.jpg"> and we want
        # the host-side render to match what the in-container render shows.
        placeholders = _placeholder_assets()
        for ph_name, ph_path in placeholders.items():
            shutil.copy2(ph_path, scratch / ph_name)
        scratch_screens = scratch / "screenshots"
        render_site(scratch, scratch_screens)
        screenshots = {png.stem: png for png in scratch_screens.glob("*.png")}

        print(f"[{spec.slug}] packing as Harbor task at {out_dir}…")
        return build_task_dir(
            out_dir,
            files=files,
            screenshots=screenshots,
            description=(
                f"Replicate a synthesised {spec.archetype} website "
                f"({spec.brand.name}) from screenshots."
            ),
            metadata={
                "source": "synthesised",
                "archetype": spec.archetype,
                "vertical": spec.vertical,
                "difficulty": spec.difficulty,
                "category": "synth",
            },
            bookkeeping={
                "source": "synthesised",
                "spec": spec.to_dict(),
                "compiler_model": COMPILER_MODEL,
            },
            keywords=("web", "html", "css", "visual", "synth", spec.archetype),
            assets=placeholders,
            force=force,
        )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument(
        "--vertical",
        help="Vertical name (templates/verticals/). Pair with --style.",
    )
    src.add_argument(
        "--random", action="store_true", dest="random_pair",
        help="Pick a random compatible (vertical, style) pair.",
    )
    src.add_argument(
        "--spec", type=Path,
        help="Path to a JSON spec file (bypasses the registry).",
    )
    p.add_argument(
        "--style",
        help="Style name (templates/styles/). Required with --vertical.",
    )
    p.add_argument("--seed", type=int, default=0,
                   help="RNG seed for sampling within the (vertical, style).")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--force", action="store_true")
    args = p.parse_args()

    # Resolve spec
    if args.spec is not None:
        spec = WebsiteSpec.from_json(args.spec.read_text())
    elif args.random_pair:
        from templates import random_spec
        v_name, s_name, spec = random_spec(args.seed)
        print(f"[random] picked vertical={v_name!r} style={s_name!r} (seed={args.seed})")
    else:
        if not args.style:
            p.error("--style is required when --vertical is given")
        from templates import sample_spec
        try:
            spec = sample_spec(args.vertical, args.style, args.seed)
        except ValueError as e:
            p.error(str(e))

    try:
        out = synthesize_task(spec, args.out, force=args.force)
    except Exception:
        traceback.print_exc()
        return 1
    print(f"\n[{spec.slug}] task written: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
