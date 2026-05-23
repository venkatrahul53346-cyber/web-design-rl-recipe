"""ecom_storefront (A5) — direct-to-consumer fashion / lifestyle e-commerce."""
from templates.verticals._base import VerticalMeta

META = VerticalMeta(
    name="ecom_storefront",
    archetype="A5",
    difficulty="hard",
    topic_description=(
        "A direct-to-consumer e-commerce site for a fashion / "
        "lifestyle brand. The brand is small, considered, makes a "
        "limited product range. The site sells objects via "
        "photography. Index is editorial: full-bleed hero + a few "
        "categories. Collection page (PLP) has filter rail + product "
        "grid. PDP is large image + product info + variant picker + "
        "CTA. Cart is line items + checkout. About tells the brand "
        "story. Journal is editorial-style blog posts. Quiet, "
        "considered, no discount-driven urgency."
    ),
    page_hints={
        "index": "Large editorial hero with full-bleed product image "
                 "+ minimal headline + CTA. Below: 'shop by category' "
                 "grid (3-4 tiles), then a featured-products row.",
        "collection": "Left rail of filters (size, color, category, "
                      "price range — checkbox lists with hairline "
                      "dividers), right grid of products (3-4 col). "
                      "Each tile: image, name, price, swatch row.",
        "PDP": "Large image left, product info right (name, price, "
               "short description, size selector, color swatches, "
               "primary CTA, longer description accordion).",
        "cart": "Line items table, subtotal/shipping/total stack, "
                "checkout CTA, related products row.",
        "about": "Brand story prose with photography. Founder quote, "
                 "production process, values.",
        "journal": "Blog-style list of editorial posts. Image + title + "
                   "excerpt for each.",
    },
    sitemap_pool=["index", "collection", "PDP", "cart", "about", "journal"],
    sitemap_min=6, sitemap_max=6,
    brand_verticals=["ecom-fashion"],
    references=["allbirds.com", "everlane.com", "muji.com"],
)
